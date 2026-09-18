import os
import subprocess

def git(root,*args):
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull}
    tls=['-c','http.sslBackend=openssl'] if os.name=='nt' else []
    result=subprocess.run(['git',*tls,'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','protocol.file.allow=never',*args],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    if result.returncode: raise ValueError(result.stderr[:1500])
    return result.stdout[:100_000]

def history(root,path=None):
    try:
        args=['log','-15','--format=%h%x09%an%x09%ad%x09%s','--date=short']
        if path: args+=['--',path]
        return [dict(zip(['commit','author','date','subject'],line.split('\t',3))) for line in git(root,*args).splitlines()]
    except (ValueError,subprocess.TimeoutExpired): return []

def blame(root,path):
    return git(root,'blame','--line-porcelain','--',path)

def show(root,commit):
    import re
    if not re.fullmatch(r'[0-9a-f]{7,40}',commit): raise ValueError('Invalid commit hash')
    return git(root,'show','--format=fuller','--stat','--patch',commit,'--')
