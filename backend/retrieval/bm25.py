import math
import re
from collections import Counter

def tokens(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return re.findall(r'[a-z0-9]+', text.lower())

class BM25:
    def __init__(self, chunks):
        self.chunks=chunks
        self.docs=[Counter(tokens(c['path']+' '+c['text'])) for c in chunks]
        self.lengths=[sum(d.values()) for d in self.docs]
        self.avg=sum(self.lengths)/max(1,len(chunks)) or 1
        self.df=Counter(t for d in self.docs for t in d)
    def search(self, query, k=10):
        scores=[]
        for i,d in enumerate(self.docs):
            score=0
            for t in set(tokens(query)):
                f=d[t]
                idf=math.log(1+(len(self.docs)-self.df[t]+0.5)/(self.df[t]+0.5))
                score+=idf*f*2.5/(f+1.5*(0.25+0.75*self.lengths[i]/self.avg))
            if score>0: scores.append((i,score))
        return sorted(scores,key=lambda x:x[1],reverse=True)[:k]
