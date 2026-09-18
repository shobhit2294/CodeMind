"""Optional real embeddings; never label keyword scores as semantic search."""
import os
import threading
import numpy as np
from backend.config import DATA

_models={}
_lock=threading.Lock()

class SemanticIndex:
    def __init__(self, chunks):
        self.model=None; self.matrix=None; self.error=None
        name=os.getenv('SEMANTIC_MODEL','')
        if not name: return
        try:
            os.environ.setdefault('HF_HOME',str(DATA/'huggingface'))
            from fastembed import TextEmbedding
            with _lock:
                if name not in _models: _models[name]=TextEmbedding(model_name=name,cache_dir=str(DATA/'embeddings'),threads=2)
                self.model=_models[name]
            if chunks:
                self.matrix=np.array(list(self.model.passage_embed([c['path']+'\n'+c['text'] for c in chunks])),dtype=np.float32)
                self.matrix/=np.maximum(np.linalg.norm(self.matrix,axis=1,keepdims=True),1e-12)
        except Exception as e:
            self.error=f'Embedding model unavailable: {type(e).__name__}'
    def search(self,query,k=10):
        if self.model is None or self.matrix is None: return []
        q=np.array(list(self.model.query_embed([query]))[0],dtype=np.float32)
        q/=max(float(np.linalg.norm(q)),1e-12)
        scores=self.matrix@q
        return [(int(i),float(scores[i])) for i in np.argsort(-scores)[:k] if scores[i]>0]
