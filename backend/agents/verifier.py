def verify(baseline,result,static,changed):
    if not static['passed']: return {'verdict':'rejected','reason':'Static syntax checks failed'}
    if not changed: return {'verdict':'rejected','reason':'No source changes'}
    if result.get('status')=='unavailable': return {'verdict':'unverified','reason':result.get('reason','Docker unavailable')}
    if result.get('status')!='passed': return {'verdict':'rejected','reason':'Sandbox tests did not pass'}
    before={t['name']:t['status'] for t in baseline.get('tests',[])}
    after={t['name']:t['status'] for t in result.get('tests',[])}
    if any(after.get(n)!='passed' for n,s in before.items() if s in {'passed','failed'}):
        return {'verdict':'rejected','reason':'A baseline test disappeared or regressed'}
    if any(s=='failed' and after.get(n)=='passed' for n,s in before.items()):
        return {'verdict':'verified','reason':'Baseline failure reproduced; the same test now passes and no observed test regressed'}
    return {'verdict':'tests_passed','reason':'Tests pass, but the reported bug was not reproduced by a failing baseline test'}
