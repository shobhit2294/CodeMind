import httpx,time,json
from pathlib import Path
client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=20)
r=client.post('/api/repos',json={'url':'https://github.com/shobhit2294/model-forge-ai'})
r.raise_for_status()
id=r.json()['id']
print('Import started: '+id,flush=True)
for _ in range(70):
    time.sleep(1)
    item=client.get('/api/repos/'+id).json()
    if item['status'] not in {'queued','indexing'}:
        Path('artifacts/github-import.json').write_text(json.dumps(item,indent=2),encoding='utf-8')
        print(json.dumps(item),flush=True)
        if item['status']!='ready': raise RuntimeError(item.get('error'))
        result=client.post('/api/repos/'+id+'/search',json={'query':'FastAPI prediction model'}).json()
        assert result['results'], result
        print('Repository search passed')
        break
else: raise RuntimeError('Import timed out')

