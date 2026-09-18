import json
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.config import DATA, REPOS, TASKS, ROOT
from backend.memory.memory import Memory
from backend.code_engine.repo_analyzer import analyze_repo
from backend.retrieval.hybrid import HybridSearch
from backend.git.history import git, history, show
from backend.git.diff import unified
from backend.execution.sandbox import snapshot, validate_changes, static_check
from backend.execution.docker_runner import run_tests
from backend.agents.llm import GroqClient
from backend.agents.planner import plan
from backend.agents.debugger import diagnose
from backend.agents.coder import code
from backend.agents.verifier import verify

DEMO_FILES={
 'pricing.py': 'def total_after_discount(prices, discount_percent):\n    """Return order total after a percentage discount."""\n    if not 0 <= discount_percent <= 100:\n        raise ValueError("Discount must be between 0 and 100")\n    subtotal = sum(prices)\n    return round(subtotal - discount_percent, 2)\n',
 'orders.py': 'from pricing import total_after_discount\n\ndef checkout(prices, discount_percent=0):\n    return {"total": total_after_discount(prices, discount_percent), "currency": "INR"}\n',
 'tests/test_pricing.py': 'import pytest\nfrom pricing import total_after_discount\n\ndef test_percentage_discount():\n    assert total_after_discount([100, 100], 10) == 180\n\ndef test_no_discount():\n    assert total_after_discount([20, 30], 0) == 50\n\ndef test_full_discount():\n    assert total_after_discount([20, 30], 100) == 0\n\ndef test_invalid_discount():\n    with pytest.raises(ValueError):\n        total_after_discount([10], 101)\n',
 'tests/integration/test_checkout.py': 'from orders import checkout\n\ndef test_checkout_discount():\n    assert checkout([50, 50, 100], 25) == {"total": 150, "currency": "INR"}\n',
 'tests/regression/test_empty.py': 'from pricing import total_after_discount\n\ndef test_empty_cart():\n    assert total_after_discount([], 10) == 0\n',
 'README.md':'# Discount service\nA small Python checkout service. Run python -m pytest.\n',
 'requirements.txt':'pytest\n'
}

class Service:
    def __init__(self):
        self.memory=Memory(DATA/'codemind.sqlite3')
        self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='codemind')
        self.indexes={}; self.lock=threading.RLock()
        for kind in ['repo','task']:
            for item in self.memory.list(kind):
                if item.get('status') in {'queued','running','indexing'}:
                    item.update(status='interrupted',error='Application restarted; start a new task to retry')
                    self.memory.put(kind,item['id'],item)
    def room(self):
        active=sum(i.get('status') in {'queued','running','indexing'} for k in ['repo','task'] for i in self.memory.list(k))
        if active>=6: raise ValueError('Six jobs are already pending; wait for one to finish')
    def import_repo(self,url=None,demo=False):
        with self.lock:
            self.room()
            if not demo and not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?',url or ''):
                raise ValueError('Use a public https://github.com/owner/repository URL')
            id=uuid.uuid4().hex
            item={'id':id,'name':'Discount service · demo' if demo else url.rstrip('/').split('/')[-1].removesuffix('.git'),'url':url,'demo':demo,'status':'queued'}
            self.memory.put('repo',id,item); self.pool.submit(self._import,id)
            return item
    def _import(self,id):
        item=self.memory.get('repo',id); root=REPOS/id
        try:
            item['status']='indexing'; self.memory.put('repo',id,item)
            if item['demo']:
                snapshot(DEMO_FILES,root)
                git(root,'init'); git(root,'add','.')
                git(root,'-c','user.name=CodeMind Demo','-c','user.email=demo@example.invalid','commit','-m','Introduce checkout and discount tests')
            else:
                git(REPOS,'clone','--depth=30','--single-branch','--no-tags','--',item['url'],str(root))
            analysis=analyze_repo(root)
            if not analysis['files']: raise ValueError('No supported source files found')
            self.memory.put('analysis',id,analysis)
            item.update(status='ready',summary=analysis['summary'],parse_errors=analysis['parse_errors'],history=history(root))
        except Exception as e: item.update(status='error',error=str(e)[:2000])
        self.memory.put('repo',id,item)
    def search(self,id,query,mode='hybrid',k=8):
        with self.lock:
            if id not in self.indexes: self.indexes[id]=HybridSearch(self.memory.get('analysis',id))
            index=self.indexes[id]
        result=index.search(query,k,mode)
        result['history']=history(REPOS/id,result['results'][0]['path']) if result['results'] else []
        return result
    def start_task(self,repo_id,issue,profile,demo=False,max_attempts=3):
        with self.lock:
            self.room(); repo=self.memory.get('repo',repo_id)
            if repo['status']!='ready': raise ValueError('Repository is not ready')
            if demo and not repo['demo']: raise ValueError('Demo fixes only operate on the bundled demo')
            if not demo:
                from backend.config import settings
                if not settings()['configured']: raise ValueError('Add GROQ_API_KEY to .env and restart the backend')
            id=uuid.uuid4().hex
            task={'id':id,'repo_id':repo_id,'issue':issue,'profile':profile,'demo':demo,'max_attempts':max_attempts,'status':'queued','attempts':[],'cancel_requested':False}
            self.memory.put('task',id,task); self.pool.submit(self._task,id)
            return task
    def cancel(self,id):
        with self.lock:
            item=self.memory.get('task',id); item['cancel_requested']=True; self.memory.put('task',id,item)
        return item
    def save(self,task):
        with self.lock:
            current=self.memory.get('task',task['id'])
            task['cancel_requested']=current.get('cancel_requested',False)
            self.memory.put('task',task['id'],task)
    def check(self,id):
        if self.memory.get('task',id).get('cancel_requested'): raise InterruptedError('Cancelled at the next stage boundary')
    def _task(self,id):
        task=self.memory.get('task',id); client=GroqClient()
        def event(stage,data):
            self.check(id); self.memory.event(id,stage,data)
        try:
            task['status']='running'; self.save(task)
            analysis=self.memory.get('analysis',task['repo_id']); original=analysis['files']
            event('understand',analysis['summary'])
            experiences=[x for x in self.memory.list('experience') if x['repo_id']==task['repo_id']][:5]
            task['plan']={'summary':'Demonstrate the repair pipeline with a scripted percentage-discount patch','steps':['Locate discount calculation','Run baseline tests','Correct percentage arithmetic','Repeat the same tests'],'queries':['discount percentage total checkout']} if task['demo'] else plan(client,task['issue'],analysis['summary'],experiences)
            event('plan',task['plan']); self.save(task)
            context={}
            for q in task['plan']['queries']:
                for c in self.search(task['repo_id'],q,k=5)['results']: context[c['id']]=c
            task['evidence']=list(context.values())[:12]
            event('retrieve',task['evidence'])
            commits=history(REPOS/task['repo_id'])
            recent_diffs=[]
            for commit in commits[:2]:
                try: recent_diffs.append({'commit':commit['commit'],'patch':show(REPOS/task['repo_id'],commit['commit'])[:2200]})
                except ValueError: pass
            history_data={'commits':commits[:8],'recent_diffs':recent_diffs}
            event('git',history_data)
            baseline=run_tests(original,task['profile']); task['baseline']=baseline
            event('baseline',baseline); self.save(task)
            for attempt in range(1,task['max_attempts']+1):
                self.check(id)
                diagnosis={'hypothesis':'The percentage is subtracted as an absolute amount','evidence':['pricing.py:6'],'uncertainty':'Scripted demo diagnosis, not generated by Groq'} if task['demo'] else diagnose(client,task['issue'],task['evidence'],baseline,history_data,[{'verdict':a['verification'],'output':a['tests'].get('output','')[:4000]} for a in task['attempts']])
                event('diagnose',diagnosis)
                paths=list(dict.fromkeys(c['path'] for c in task['evidence']))[:8]
                selected={p:original[p] for p in paths if len(original[p])<18_000}
                # Bound full-file context so free-tier requests stay manageable.
                selected=dict(list(selected.items())[:6])
                if sum(map(len,selected.values()))>26_000: raise ValueError('Selected files exceed the model context budget; narrow the issue')
                patch={'explanation':'Use subtotal multiplied by the remaining percentage','changes':{'pricing.py':original['pricing.py'].replace('subtotal - discount_percent','subtotal * (1 - discount_percent / 100)')}} if task['demo'] else code(client,task['issue'],diagnosis,selected,task['attempts'][-1]['tests'].get('output','')[:5000] if task['attempts'] else '')
                try:
                    candidate=validate_changes(original,patch['changes'])
                except (ValueError,SyntaxError) as e:
                    event('patch_rejected',{'attempt':attempt,'reason':str(e)})
                    task['attempts'].append({'attempt':attempt,'diagnosis':diagnosis,'explanation':patch['explanation'],'diff':'','changes':{},'tests':{'status':'not_run','output':str(e)},'static':{'passed':False},'verification':{'verdict':'rejected','reason':str(e)}})
                    self.save(task); continue
                diff=unified(original,candidate); event('patch',{'attempt':attempt,'diff':diff,'explanation':patch['explanation']})
                snapshot(candidate,TASKS/id/f'attempt-{attempt}')
                static=static_check(candidate)
                result=run_tests(candidate,task['profile']) if static['passed'] else {'status':'not_run'}
                verdict=verify(baseline,result,static,bool(diff))
                record={'attempt':attempt,'diagnosis':diagnosis,'explanation':patch['explanation'],'diff':diff,'changes':patch['changes'],'tests':result,'static':static,'verification':verdict}
                task['attempts'].append(record); event('verify',record); self.save(task)
                if verdict['verdict'] in {'verified','tests_passed','unverified'}: break
            task['status']='completed'
            task['result']=task['attempts'][-1]['verification']
            self.memory.put('experience',id,{'repo_id':task['repo_id'],'issue':task['issue'],'result':task['result'],'attempts':len(task['attempts']),'approaches':[{'hypothesis':a['diagnosis']['hypothesis'],'explanation':a['explanation'],'outcome':a['verification']} for a in task['attempts']]})
            event('complete',task['result'])
        except InterruptedError as e: task.update(status='cancelled',error=str(e))
        except Exception as e:
            task.update(status='error',error=str(e)[:2000]); self.memory.event(id,'error',{'message':task['error']})
        finally: self.save(task)
