"""Reproducible retrieval ablation. Scores measure this tiny fixture, not general SWE ability."""
import json
import tempfile
import time
from pathlib import Path
from backend.service import DEMO_FILES
from backend.execution.sandbox import snapshot
from backend.code_engine.repo_analyzer import analyze_repo
from backend.retrieval.hybrid import HybridSearch
from evaluation.metrics import reciprocal_rank,recall_at_k

def benchmark():
    cases=json.loads((Path(__file__).parent/'datasets/retrieval.json').read_text())
    with tempfile.TemporaryDirectory() as d:
        snapshot(DEMO_FILES,Path(d)); search=HybridSearch(analyze_repo(Path(d)))
    reports=[]
    for mode in ['keyword','semantic','hybrid']:
        rows=[]
        for c in cases:
            started=time.perf_counter(); result=search.search(c['query'],k=5,mode=mode)
            paths=list(dict.fromkeys(r['path'] for r in result['results']))
            rows.append({'query':c['query'],'paths':paths,'mrr':reciprocal_rank(paths,c['relevant']),'recall_at_5':recall_at_k(paths,c['relevant']),'latency_ms':round((time.perf_counter()-started)*1000,3)})
        reports.append({'mode':mode,'enabled':mode!='semantic' or search.semantic.matrix is not None,'mrr':sum(r['mrr'] for r in rows)/len(rows),'recall_at_5':sum(r['recall_at_5'] for r in rows)/len(rows),'cases':rows})
    return {'dataset':'bundled discount-service fixture','query_count':len(cases),'warning':'Small transparent fixture, not SWE-bench or evidence of general repair quality. Disabled semantic scores are not an ablation result.','reports':reports}

if __name__=='__main__': print(json.dumps(benchmark(),indent=2))
