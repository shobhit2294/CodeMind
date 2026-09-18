import pytest
import httpx
from backend.agents.llm import GroqClient
from backend.agents.planner import plan

def test_groq_request_contract(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    captured={}
    def post(self,url,**kwargs):
        captured.update(kwargs); captured['url']=url
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"Investigate","steps":["Search"],"queries":["discount"]}'}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    assert plan(GroqClient(),'broken discount',{})['queries']==['discount']
    assert captured['url']=='https://api.groq.com/openai/v1/chat/completions'
    assert captured['json']['response_format']['type']=='json_schema'
    assert captured['json']['response_format']['json_schema']['strict'] is True

def test_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    with pytest.raises(ValueError,match='GROQ_API_KEY'):GroqClient().complete('system',{})

def test_invalid_model_shape_rejected(monkeypatch):
    class Fake:
        def complete(self,*args):return {'summary':'Missing steps'}
    with pytest.raises(ValueError):plan(Fake(),'issue',{})

def test_oversized_context_is_not_silently_truncated(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    with pytest.raises(ValueError,match='context exceeds'):
        GroqClient().complete('system',{'code':'x'*40000})

def test_provider_extra_searches_are_bounded():
    class Provider:
        def complete(self,*args):
            return {'summary':'Investigate','steps':['Inspect code'],'queries':['discount','total','checkout','validation','extra']}
    assert plan(Provider(),'Discount is wrong',{})['queries']==['discount','total','checkout','validation']

def test_schema_error_retries_with_provider_feedback(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test-key')
    calls=[]
    def post(self,url,**kwargs):
        calls.append(kwargs)
        if len(calls)==1:
            return httpx.Response(400,json={'error':{'message':'JSON does not match schema: missing queries'}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"Investigate","steps":["Inspect"],"queries":["discount"]}'}}]})
    monkeypatch.setattr(httpx.Client,'post',post)
    assert plan(GroqClient(),'Discount is incorrect',{})['queries']==['discount']
    assert len(calls)==2
    assert 'missing queries' in calls[1]['json']['messages'][0]['content']

def test_coder_rejects_duplicate_paths():
    from backend.agents.coder import code
    class Provider:
        def complete(self,*args): return {'explanation':'Fix','changes':[{'path':'a.py','content':'x=1'},{'path':'a.py','content':'x=2'}]}
    with pytest.raises(ValueError,match='duplicate'):
        code(Provider(),'Issue',{}, {'a.py':'x=0'},'')
