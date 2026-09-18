import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.config import ROOT
from backend.service import Service
from backend.api.routes import router

@asynccontextmanager
async def lifespan(app):
    app.state.service=Service()
    yield
    app.state.service.pool.shutdown(wait=True,cancel_futures=True)

def create_app():
    app=FastAPI(title='CodeMind',version='0.1.0',lifespan=lifespan)
    allowed_hosts=['localhost','127.0.0.1','testserver','backend']
    allowed_origins={'http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000'}
    # Render supplies this service's exact public hostname. Do not trust every
    # onrender.com site or derive allowed origins from incoming request headers.
    render_host=os.getenv('RENDER_EXTERNAL_HOSTNAME','').strip().lower()
    if render_host:
        if not all(part and all(c.isascii() and (c.isalnum() or c=='-') for c in part) for part in render_host.split('.')):
            raise ValueError('RENDER_EXTERNAL_HOSTNAME must be a hostname without a scheme, port, or path')
        allowed_hosts.append(render_host)
        allowed_origins.add('https://'+render_host)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=allowed_hosts)

    @app.middleware('http')
    async def local_origin(request:Request,call_next):
        origin=request.headers.get('origin')
        if request.method not in {'GET','HEAD','OPTIONS'} and origin and origin not in allowed_origins:
            return JSONResponse({'detail':'Origin not permitted'},status_code=403)
        return await call_next(request)

    @app.exception_handler(KeyError)
    async def missing(request,exc): return JSONResponse({'detail':'Object not found'},status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(request,exc): return JSONResponse({'detail':str(exc)},status_code=400)

    app.include_router(router)
    dist=ROOT/'frontend'/'dist'
    if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app

app=create_app()
