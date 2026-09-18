"""Exercise the real provider through the application; never print credentials."""
import json
import time
from pathlib import Path
import httpx

client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=30)
repo=next(r for r in client.get('/api/repos').json() if r.get('demo') and r['status']=='ready')
response=client.post('/api/tasks',json={'repo_id':repo['id'],'issue':'Fix total_after_discount: discount_percent is a percentage of the subtotal, not an absolute amount. Preserve validation and make the existing checkout and empty-cart tests pass.','profile':'pytest','demo':False,'max_attempts':2})
response.raise_for_status()
id=response.json()['id']
print('Live Groq investigation started: '+id,flush=True)
for _ in range(120):
    task=client.get('/api/tasks/'+id).json()
    if task['status'] not in {'queued','running'}:
        Path('artifacts/groq-live-check.json').write_text(json.dumps(task,indent=2),encoding='utf-8')
        print(json.dumps({'status':task['status'],'result':task.get('result'),'error':task.get('error'),'attempts':len(task['attempts']),'stages':[e['stage'] for e in task.get('events',[])]}),flush=True)
        if task['status']!='completed':raise RuntimeError('Live workflow failed; see local report')
        assert task['attempts'][-1]['changes'], 'No proposed source changes'
        break
    time.sleep(1)
else:raise RuntimeError('Workflow still running; inspect it in the app')
