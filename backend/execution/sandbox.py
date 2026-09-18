from pathlib import Path
import ast
import shutil
from backend.code_engine.parser import safe_path

def snapshot(files,destination:Path):
    destination.mkdir(parents=True,exist_ok=True)
    for name,content in files.items():
        p=safe_path(destination,name); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8')

def validate_changes(files,changes):
    if not changes or len(changes)>8: raise ValueError('A patch must change 1–8 files')
    output=dict(files)
    for name,content in changes.items():
        safe_path(Path.cwd()/'validation-root',name)
        if name not in files: raise ValueError('Only existing source files may be patched in this version')
        lower=name.lower()
        if any(p.startswith('test') or p in {'__tests__','.github'} for p in Path(lower).parts) or Path(lower).name in {'conftest.py','pytest.ini','pyproject.toml','package.json','setup.cfg','setup.py'} or lower.endswith(('_test.py','.test.js','.test.ts','.spec.js','.spec.ts','.test.tsx','.spec.tsx','.test.jsx','.spec.jsx')):
            raise ValueError('Existing tests and execution configuration are protected')
        if not name.endswith(('.py','.js','.jsx','.ts','.tsx')): raise ValueError('Only source-code changes are supported')
        if not isinstance(content,str) or len(content)>180_000: raise ValueError('Invalid file content')
        if name.endswith('.py'): ast.parse(content,filename=name)
        output[name]=content
    if output==files: raise ValueError('Patch contains no changes')
    return output

def static_check(files):
    errors=[]
    for name,source in files.items():
        if name.endswith('.py'):
            try: ast.parse(source,filename=name)
            except SyntaxError as e: errors.append(f'{name}:{e.lineno}: {e.msg}')
    return {'passed':not errors,'errors':errors,'scope':'Python syntax; no code imported or executed on host'}
