from .bm25 import BM25
from .semantic import SemanticIndex

class HybridSearch:
    def __init__(self,analysis):
        self.analysis=analysis; self.chunks=analysis['chunks']
        self.bm25=BM25(self.chunks); self.semantic=SemanticIndex(self.chunks)
    def search(self,query,k=8,mode='hybrid'):
        ranks={}; reasons={}
        channels=[]
        if mode!='semantic': channels.append(('keyword',self.bm25.search(query,k*3)))
        if mode!='keyword': channels.append(('semantic',self.semantic.search(query,k*3)))
        for name,items in channels:
            for rank,(idx,_) in enumerate(items):
                ranks[idx]=ranks.get(idx,0)+1/(60+rank+1)
                reasons.setdefault(idx,[]).append(name)
        if mode=='hybrid':
            seeds={self.chunks[i]['path'] for i in sorted(ranks,key=ranks.get,reverse=True)[:3]}
            neighbors=set()
            for e in self.analysis['graph']['edges']:
                a,b=e['source'].split('::')[0],e['target'].split('::')[0]
                if a in seeds: neighbors.add(b)
                if b in seeds: neighbors.add(a)
            for p in neighbors-seeds:
                idx=next((i for i,c in enumerate(self.chunks) if c['path']==p),None)
                if idx is not None and idx not in ranks:
                    ranks[idx]=0.5/65
                    reasons.setdefault(idx,[]).append('graph')
        return {'results':[{**self.chunks[i],'score':round(ranks[i],5),'via':reasons[i]} for i in sorted(ranks,key=ranks.get,reverse=True)[:k]],
                'semantic_enabled':self.semantic.matrix is not None,'semantic_error':self.semantic.error}
