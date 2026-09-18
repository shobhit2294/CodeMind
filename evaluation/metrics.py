def reciprocal_rank(actual,expected):
    return next((1/(i+1) for i,p in enumerate(actual) if p in expected),0.0)

def recall_at_k(actual,expected,k=5):
    return len(set(actual[:k])&set(expected))/len(set(expected)) if expected else 0.0

def repair_rate(verdicts):
    return sum(v=='verified' for v in verdicts)/len(verdicts) if verdicts else 0.0
