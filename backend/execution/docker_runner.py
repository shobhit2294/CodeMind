import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid

def availability():
    if not shutil.which('docker'): return {'available':False,'reason':'Docker CLI is not installed'}
    try:
        p=subprocess.run(['docker','info','--format','{{.ServerVersion}}'],capture_output=True,text=True,timeout=6)
        if p.returncode: return {'available':False,'reason':'Start Docker Desktop (Linux containers) to run tests'}
        image=os.getenv('SANDBOX_IMAGE','codemind-sandbox:local')
        p=subprocess.run(['docker','image','inspect',image],capture_output=True,timeout=6)
        return {'available':p.returncode==0,'reason':None if p.returncode==0 else 'Build the sandbox image: docker build -t codemind-sandbox:local sandbox'}
    except (OSError,subprocess.TimeoutExpired): return {'available':False,'reason':'Docker is not responding'}

def run_tests(files,profile='pytest'):
    if profile not in {'pytest','node-test'}: raise ValueError('Unsupported test profile')
    ready=availability()
    if not ready['available']: return {'status':'unavailable',**ready}
    name='codemind-'+uuid.uuid4().hex
    timeout=max(10,min(int(os.getenv('SANDBOX_TIMEOUT','90')),180))
    command=['docker','run','--rm','-i','--name',name,'--network=none','--read-only','--cpus=1','--memory=512m','--memory-swap=512m','--pids-limit=96','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--tmpfs','/work:rw,nosuid,nodev,size=128m,mode=1777','--tmpfs','/tmp:rw,nosuid,nodev,size=32m,mode=1777','--log-driver=none',os.getenv('SANDBOX_IMAGE','codemind-sandbox:local')]
    process=None
    try:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output=bytearray(); overflow=threading.Event()
        def collect():
            while True:
                chunk=process.stdout.read(4096)
                if not chunk: break
                if len(output)+len(chunk)>100_000:
                    overflow.set(); process.kill(); break
                output.extend(chunk)
        def feed():
            try:
                process.stdin.write(json.dumps({'files':files,'profile':profile}).encode())
                process.stdin.close()
            except (OSError,ValueError): pass
        reader=threading.Thread(target=collect,daemon=True); reader.start()
        writer=threading.Thread(target=feed,daemon=True); writer.start()
        process.wait(timeout=timeout); reader.join(timeout=3); writer.join(timeout=3)
        if overflow.is_set(): return {'status':'error','reason':'Sandbox output exceeded 100 KB'}
        raw=output.decode('utf-8',errors='replace')
        try: data=json.loads(raw)
        except json.JSONDecodeError: return {'status':'error','reason':raw[:3000] or 'Sandbox produced no report'}
        if process.returncode: return {'status':'error','reason':raw[:3000]}
        if not isinstance(data,dict): return {'status':'error','reason':'Invalid sandbox report'}
        return data
    except subprocess.TimeoutExpired:
        if process: process.kill(); process.wait(timeout=5)
        return {'status':'timeout','reason':f'Sandbox exceeded {timeout}s'}
    finally:
        try: subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired): pass
