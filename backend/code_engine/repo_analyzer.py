from collections import Counter
from .parser import read_sources
from .ast_analyzer import analyze
from .dependency_graph import build_graph

def analyze_repo(root):
    files, omitted = read_sources(root)
    analyses = {p: analyze(p,s) for p,s in files.items()}
    chunks=[]
    for p, text in files.items():
        lines=text.splitlines()
        for start in range(0,len(lines),60):
            chunks.append({'id':f'{p}:{start+1}', 'path':p,'line':start+1,'end':min(start+80,len(lines)), 'text':'\n'.join(lines[start:start+80])})
    deps='\n'.join(s.lower() for p,s in files.items() if p.endswith(('requirements.txt','pyproject.toml','package.json')))
    frameworks=[n for n in ['fastapi','django','flask','react','next','express','postgres','redis','sqlalchemy'] if n in deps]
    return {'files':files, 'chunks':chunks, 'graph':build_graph(files,analyses),
            'summary':{'file_count':len(files),'chunk_count':len(chunks),'symbol_count':sum(len(a['symbols']) for a in analyses.values()),
                       'languages':dict(Counter(p.rsplit('.',1)[-1] for p in files)), 'frameworks':frameworks,
                       'modules':sorted({p.split('/')[0] for p in files if '/' in p}), 'omitted_count':len(omitted)},
            'omitted':omitted, 'parse_errors':[e for a in analyses.values() for e in a['errors']]}
