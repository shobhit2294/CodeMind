from pydantic import BaseModel, Field, ConfigDict

class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    summary:str
    steps:list[str]=Field(min_length=1,max_length=8)
    queries:list[str]=Field(min_length=1,max_length=4)

def plan(client,issue,summary,experiences=None):
    output=client.complete('You plan a repository bug investigation. JSON fields: summary (string), steps (1–8 strings), queries (1–4 targeted code search queries). Use previous outcomes to avoid repeating failed approaches.',{'issue':issue,'repository':summary,'previous_outcomes':experiences or []},Plan.model_json_schema())
    # Bound plans from alternative clients as well as the strict Groq provider.
    if isinstance(output,dict):
        for field,limit in [('steps',8),('queries',4)]:
            if isinstance(output.get(field),list): output[field]=output[field][:limit]
    return Plan.model_validate(output).model_dump()
