"""Trusted container entrypoint. No host volumes, keys, network or Docker socket."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import resource
import xml.etree.ElementTree as ET

def main():
    resource.setrlimit(resource.RLIMIT_FSIZE, (2_000_000,2_000_000))
    data=json.loads(sys.stdin.buffer.read(15_000_000))
    root=Path('/work')
    for name,content in data['files'].items():
        p=(root/name).resolve()
        if not p.is_relative_to(root) or name.startswith('/') or '\\' in name: raise ValueError('Invalid input path')
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8')
    env={**os.environ,'PYTHONPATH':'/work','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','CI':'true'}
    if data['profile']=='pytest':
        cmd=['python','-m','pytest','-q','-p','no:cacheprovider','--junitxml=/tmp/results.xml']
    else: cmd=['node','--test','--test-reporter=tap']
    with tempfile.TemporaryFile() as log:
        try:
            p=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=log,timeout=70)
            code=p.returncode
        except subprocess.TimeoutExpired:
            code=124
        log.seek(0); output=log.read(40_000).decode(errors='replace')
    tests=[]
    if data['profile']=='pytest' and Path('/tmp/results.xml').exists():
        for case in ET.parse('/tmp/results.xml').iter('testcase'):
            failure=case.find('failure'); error=case.find('error'); skip=case.find('skipped')
            status='failed' if failure is not None else 'error' if error is not None else 'skipped' if skip is not None else 'passed'
            identity=case.attrib.get('classname','')+'::'+case.attrib.get('name','')
            suite='integration' if 'integration' in identity else 'regression' if 'regression' in identity else 'unit'
            tests.append({'name':identity,'status':status,'suite':suite})
    elif data['profile']=='node-test':
        for match in re.finditer(r'^(not ok|ok) \d+ - (.+)$',output,re.M):
            tests.append({'name':match[2],'status':'passed' if match[1]=='ok' else 'failed','suite':'unit'})
    counts={s:sum(t['status']==s for t in tests) for s in ['passed','failed','error','skipped']}
    return {'status':'passed' if code==0 and counts['passed']>0 and not counts['failed'] and not counts['error'] else 'failed', 'exit_code':code,'counts':counts,'tests':tests,'output':output,'profile':data['profile']}

if __name__=='__main__':
    try: print(json.dumps(main()))
    except Exception as e: print(json.dumps({'status':'error','reason':str(e)[:2000]}))
