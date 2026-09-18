"""Bounded source ingestion. Repository contents are data, never host commands."""
from pathlib import Path, PurePosixPath
import os

SKIP = {'.git', '.venv', 'venv', 'node_modules', 'dist', 'build', '__pycache__', '.data', '.next', 'vendor'}
EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.toml', '.md', '.yaml', '.yml', '.txt', '.sql', '.go', '.rs', '.java', '.css', '.html'}
MAX_FILES, MAX_BYTES, MAX_TOTAL = 1500, 180_000, 12_000_000

def safe_path(root: Path, name: str) -> Path:
    if not name or '\\' in name or ':' in name or name.startswith('/'):
        raise ValueError('Expected a relative repository path')
    parts = PurePosixPath(name).parts
    if any(p in {'..', '.git', '.env'} for p in parts) or any(p.startswith('.env') for p in parts):
        raise ValueError('Protected or escaping path')
    p = root / name
    if any(x.is_symlink() for x in [p, *p.parents] if x != root.parent):
        raise ValueError('Symbolic links are not supported')
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes repository')
    return p

def read_sources(root: Path):
    files, omitted, total = {}, [], 0
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not (Path(base)/d).is_symlink())
        for name in sorted(names):
            p = Path(base)/name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or name.startswith('.env') or p.suffix.lower() in {'.pem', '.key', '.p12'}:
                omitted.append(rel); continue
            if p.suffix.lower() not in EXTENSIONS or p.stat().st_size > MAX_BYTES:
                omitted.append(rel); continue
            if len(files) >= MAX_FILES or total + p.stat().st_size > MAX_TOTAL:
                omitted.append(rel); continue
            try:
                text = p.read_text(encoding='utf-8')
                if '\0' not in text:
                    files[rel] = text; total += p.stat().st_size
            except (UnicodeError, OSError):
                omitted.append(rel)
    return files, omitted
