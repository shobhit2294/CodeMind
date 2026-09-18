import difflib

def unified(before,after):
    return ''.join(''.join(difflib.unified_diff(before.get(p,'').splitlines(True),after.get(p,'').splitlines(True),fromfile='a/'+p,tofile='b/'+p)) for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p))
