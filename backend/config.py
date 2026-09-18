import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('CODEMIND_DATA', str(ROOT / '.data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
REPOS = DATA / 'repos'
TASKS = DATA / 'tasks'
REPOS.mkdir(exist_ok=True)
TASKS.mkdir(exist_ok=True)

def settings():
    return {'provider': 'Groq', 'model': os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'),
            'configured': bool(os.getenv('GROQ_API_KEY')), 'semantic_model': os.getenv('SEMANTIC_MODEL') or None}
