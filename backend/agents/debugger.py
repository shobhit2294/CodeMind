from pydantic import BaseModel, Field, ConfigDict

class Diagnosis(BaseModel):
    model_config=ConfigDict(extra='forbid')
    hypothesis:str
    evidence:list[str]=Field(max_length=8)
    uncertainty:str

def diagnose(client,issue,context,baseline,history,previous):
    context=[{**c,'text':c['text'][:1500]} for c in context[:8]]
    baseline={k:baseline[k] for k in ['status','counts','reason','exit_code'] if k in baseline}|{'output':baseline.get('output','')[:3000]}
    previous=[{**p,'output':p.get('output','')[:2000]} for p in previous[-2:]]
    return Diagnosis.model_validate(client.complete('Diagnose this issue using supplied code, Git history and test evidence. Return hypothesis, evidence (path:line references), uncertainty. Do not invent confidence scores.',{'issue':issue,'context':context,'baseline':baseline,'git':history,'previous_attempts':previous},Diagnosis.model_json_schema())).model_dump()
