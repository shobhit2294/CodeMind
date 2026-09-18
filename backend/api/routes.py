from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from backend.config import REPOS, settings
from backend.code_engine.parser import safe_path
from backend.execution.docker_runner import availability
from backend.git.history import blame, show

router=APIRouter(prefix='/api')

def service(request): return request.app.state.service

class ImportRequest(BaseModel):
    url:str=Field(max_length=300)

class SearchRequest(BaseModel):
    query:str=Field(min_length=1,max_length=2000)
    mode:Literal['hybrid','keyword','semantic']='hybrid'

class TaskRequest(BaseModel):
    repo_id:str
    issue:str=Field(min_length=8,max_length=3000)
    profile:Literal['pytest','node-test']='pytest'
    demo:bool=False
    max_attempts:int=Field(default=3,ge=1,le=3)

@router.get('/health')
def health(request:Request): return {'status':'ok','llm':settings(),'sandbox':availability()}

@router.get('/repos')
def repos(request:Request): return service(request).memory.list('repo')

@router.post('/repos',status_code=202)
def import_repo(body:ImportRequest,request:Request): return service(request).import_repo(body.url)

@router.post('/demo',status_code=202)
def demo(request:Request): return service(request).import_repo(demo=True)

@router.get('/repos/{id}')
def repo(id:str,request:Request): return service(request).memory.get('repo',id)

@router.get('/repos/{id}/graph')
def graph(id:str,request:Request): return service(request).memory.get('analysis',id)['graph']

@router.get('/repos/{id}/files')
def files(id:str,request:Request): return list(service(request).memory.get('analysis',id)['files'])

@router.get('/repos/{id}/file')
def file(id:str,path:str,request:Request):
    analysis=service(request).memory.get('analysis',id)
    if path not in analysis['files']: raise HTTPException(404,'File not indexed')
    return {'path':path,'content':analysis['files'][path]}

@router.post('/repos/{id}/search')
def search(id:str,body:SearchRequest,request:Request): return service(request).search(id,body.query,body.mode)

@router.get('/repos/{id}/git')
def git_details(id:str,request:Request,path:str|None=None,commit:str|None=None):
    service(request).memory.get('repo',id)
    if path:
        safe_path(REPOS/id,path)
        return {'output':blame(REPOS/id,path)}
    if commit: return {'output':show(REPOS/id,commit)}
    return {'history':service(request).memory.get('repo',id).get('history',[])}

@router.get('/tasks')
def tasks(request:Request): return service(request).memory.list('task')

@router.post('/tasks',status_code=202)
def start(body:TaskRequest,request:Request): return service(request).start_task(**body.model_dump())

@router.get('/tasks/{id}')
def task(id:str,request:Request): return {**service(request).memory.get('task',id),'events':service(request).memory.events(id)}

@router.post('/tasks/{id}/cancel')
def cancel(id:str,request:Request): return service(request).cancel(id)

@router.get('/tasks/{id}/patch')
def patch(id:str,request:Request):
    item=service(request).memory.get('task',id)
    if not item.get('attempts'): raise HTTPException(404,'No patch yet')
    return Response(item['attempts'][-1]['diff'],media_type='text/plain',headers={'Content-Disposition':f'attachment; filename="codemind-{id[:8]}.patch"'})

@router.get('/memory')
def memory(request:Request): return service(request).memory.list('experience')
