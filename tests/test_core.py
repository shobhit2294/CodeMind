from pathlib import Path
import pytest
from backend.code_engine.ast_analyzer import analyze
from backend.code_engine.dependency_graph import build_graph
from backend.code_engine.parser import safe_path,read_sources
from backend.code_engine.repo_analyzer import analyze_repo
from backend.retrieval.bm25 import BM25
from backend.retrieval.hybrid import HybridSearch
from backend.execution.sandbox import snapshot,validate_changes,static_check
from backend.agents.verifier import verify
from backend.memory.memory import Memory
from backend.service import DEMO_FILES
from evaluation.metrics import reciprocal_rank,recall_at_k

def test_python_graph_resolves_relative_imports():
    files={'pkg/a.py':'from .b import value\n\ndef compute():\n    return value()\n','pkg/b.py':'def value():\n    return 1\n'}
    graph=build_graph(files,{p:analyze(p,s) for p,s in files.items()})
    assert any(e['kind']=='IMPORTS' and e['target']=='pkg/b.py' for e in graph['edges'])
    assert any(e['kind']=='CALLS' and e['target']=='pkg/b.py::value' for e in graph['edges'])

def test_python_nested_symbols_and_inheritance():
    a=analyze('a.py','class Base: pass\nclass Child(Base):\n    async def run(self):\n        return 1\n')
    assert any(s['name']=='Child.run' for s in a['symbols'])
    assert a['inherits'][0]['target']=='Base'

def test_typescript_parser():
    a=analyze('src/a.ts',"import { x } from './b';\nfunction compute(): number { return x(); }")
    assert './b' in a['imports']
    assert any(s['name']=='compute' for s in a['symbols'])
    assert any(c['target']=='x' for c in a['calls'])

@pytest.mark.parametrize('path',['../escape.py','/tmp/x.py','C:/x.py','x\\y.py','.git/config','.env','nested/.env.local'])
def test_path_traversal_rejected(tmp_path,path):
    with pytest.raises(ValueError): safe_path(tmp_path,path)

def test_ingestion_omits_secrets_and_generated(tmp_path):
    (tmp_path/'.env').write_text('SECRET=secret')
    (tmp_path/'node_modules').mkdir(); (tmp_path/'node_modules/a.js').write_text('secret')
    (tmp_path/'main.py').write_text('x=1')
    files,omitted=read_sources(tmp_path)
    assert list(files)==['main.py']; assert '.env' in omitted

def test_bm25_identifiers():
    chunks=[{'path':'auth.py','text':'verify Firebase access token'},{'path':'cart.py','text':'sum cart price'}]
    assert BM25(chunks).search('Firebase token')[0][0]==0

def test_hybrid_adds_graph_neighbor(tmp_path,monkeypatch):
    monkeypatch.delenv('SEMANTIC_MODEL',raising=False)
    snapshot({'a.py':'from b import value\ndef special_token(): return value()','b.py':'def value(): return 3'},tmp_path)
    result=HybridSearch(analyze_repo(tmp_path)).search('special_token')
    assert any(r['path']=='b.py' and 'graph' in r['via'] for r in result['results'])
    assert not result['semantic_enabled']

@pytest.mark.parametrize('path',['tests/test_main.py','conftest.py','pyproject.toml','src/a.test.js'])
def test_patch_cannot_weaken_tests(path):
    with pytest.raises(ValueError): validate_changes({path:'x=1'},{path:'x=2'})

def test_patch_validation_and_syntax():
    assert validate_changes({'a.py':'x=1'},{'a.py':'x=2'})['a.py']=='x=2'
    with pytest.raises(ValueError): validate_changes({'a.py':'x=1'},{'a.py':'x=1'})
    with pytest.raises(SyntaxError): validate_changes({'a.py':'x=1'},{'a.py':'def x('})
    assert not static_check({'a.py':'def ('})['passed']

def report(status,tests): return {'status':status,'tests':[{'name':n,'status':s} for n,s in tests]}

def test_verifier_requires_reproduction():
    baseline=report('failed',[('bug','failed'),('stable','passed')])
    after=report('passed',[('bug','passed'),('stable','passed')])
    assert verify(baseline,after,{'passed':True},True)['verdict']=='verified'
    assert verify(after,after,{'passed':True},True)['verdict']=='tests_passed'

def test_verifier_rejects_disappearing_or_regressing_tests():
    baseline=report('failed',[('bug','failed'),('stable','passed')])
    for tests in [[('bug','passed')],[('bug','passed'),('stable','failed')]]:
        assert verify(baseline,report('passed',tests),{'passed':True},True)['verdict']=='rejected'

def test_verifier_never_confuses_missing_runner_with_pass():
    assert verify({}, {'status':'unavailable'}, {'passed':True},True)['verdict']=='unverified'
    assert verify({}, {'status':'timeout'}, {'passed':True},True)['verdict']=='rejected'

def test_memory_survives_reopen(tmp_path):
    path=tmp_path/'test.db'; memory=Memory(path)
    memory.put('task','a',{'status':'running'}); memory.event('a','plan',{'steps':['inspect']})
    other=Memory(path); assert other.get('task','a')['status']=='running'; assert other.events('a')[0]['stage']=='plan'

def test_retrieval_metrics():
    assert reciprocal_rank(['b','a'],['a'])==.5
    assert recall_at_k(['a'],['a','b'])==.5
