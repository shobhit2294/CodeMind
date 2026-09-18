import posixpath

def build_graph(files, analyses):
    nodes = [{'id': p, 'kind': 'file', 'label': p, 'path': p} for p in files]
    edges, symbols = [], {}
    for p, a in analyses.items():
        for s in a['symbols']:
            nodes.append({**s, 'label': s['name']}); symbols.setdefault(s['name'].split('.')[-1], []).append(s)
            edges.append({'source': p, 'target': s['id'], 'kind': 'DEFINES'})
    for p, a in analyses.items():
        for module in a['imports']:
            if p.endswith('.py'):
                level = len(module)-len(module.lstrip('.'))
                base = posixpath.dirname(p)
                for _ in range(max(0, level-1)): base = posixpath.dirname(base)
                raw = module.lstrip('.').replace('.', '/')
                target = posixpath.join(base, raw) if level else raw
                candidates = [target+'.py', target+'/__init__.py']
            else:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(p), module)) if module.startswith('.') else module
                candidates = [target] + [target+ext for ext in ['.ts','.tsx','.js','.jsx','/index.ts','/index.js']]
            found = next((v for v in candidates if v in files), None)
            if found: edges.append({'source': p, 'target': found, 'kind': 'IMPORTS'})
        for kind, key in [('CALLS','calls'), ('INHERITS','inherits')]:
            for relation in a[key]:
                candidates = symbols.get(relation['target'].split('.')[-1], [])
                local = [s for s in candidates if s['path']==p]
                candidates = local or candidates
                if len(candidates)==1:
                    edges.append({'source': relation['source'], 'target': candidates[0]['id'], 'kind': kind, 'resolution': 'static-name-match'})
    return {'nodes': nodes, 'edges': edges, 'limitations': 'Static name matching, not full type inference. Dynamic imports and ambiguous calls remain unresolved.'}
