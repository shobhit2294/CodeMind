import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.service import Service

def ready(client,id):
    for _ in range(100):
        repo=client.get('/api/repos/'+id).json()
        if repo['status'] not in {'queued','indexing'}: return repo
        time.sleep(.03)
    raise AssertionError('Repository job timed out')

def test_demo_api_and_unavailable_sandbox(tmp_path,monkeypatch):
    monkeypatch.delenv('SEMANTIC_MODEL',raising=False)
    import backend.service as module
    monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setattr(module,'REPOS',tmp_path/'repos'); module.REPOS.mkdir()
    monkeypatch.setattr(module,'TASKS',tmp_path/'tasks'); module.TASKS.mkdir()
    monkeypatch.setattr(module,'run_tests',lambda *args:{'status':'unavailable','reason':'Test fixture: no Docker'})
    with TestClient(app) as client:
        assert client.post('/api/repos',json={'url':'file:///etc'}).status_code==400
        assert client.post('/api/demo',headers={'Origin':'https://malicious.invalid'}).status_code==403
        id=client.post('/api/demo').json()['id']; repo=ready(client,id)
        assert repo['status']=='ready',repo
        assert client.get(f'/api/repos/{id}/graph').json()['edges']
        assert client.post(f'/api/repos/{id}/search',json={'query':'discount'}).json()['results']
        task=client.post('/api/tasks',json={'repo_id':id,'issue':'Discount percentage is incorrect','demo':True}).json()
        for _ in range(100):
            task=client.get('/api/tasks/'+task['id']).json()
            if task['status'] not in {'queued','running'}:break
            time.sleep(.03)
        assert task['status']=='completed',task
        assert task['result']['verdict']=='unverified'
        patch=client.get(f"/api/tasks/{task['id']}/patch")
        assert 'subtotal * (1 - discount_percent / 100)' in patch.text
        assert client.get(f'/api/repos/{id}/file',params={'path':'pricing.py'}).json()['content'].find('subtotal - discount_percent')>=0
        assert len(client.get('/api/memory').json())==1

def test_restart_marks_unfinished_work(tmp_path,monkeypatch):
    import backend.service as module
    monkeypatch.setattr(module,'DATA',tmp_path)
    first=Service(); first.memory.put('task','unfinished',{'id':'unfinished','status':'running'})
    first.pool.shutdown()
    second=Service()
    assert second.memory.get('task','unfinished')['status']=='interrupted'
    second.pool.shutdown()
