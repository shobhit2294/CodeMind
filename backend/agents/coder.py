from pydantic import BaseModel, Field, ConfigDict

class Edit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str
    content:str

class Patch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    explanation:str
    changes:list[Edit]=Field(min_length=1,max_length=8)

def code(client,issue,diagnosis,files,feedback):
    patch=Patch.model_validate(client.complete('Make a minimal fix. Return explanation and changes: a list of objects with path and content, containing COMPLETE replacement file content for existing source paths. Never modify tests, configuration, dependencies, or unrelated files. Preserve public interfaces unless the issue requires a change.',{'issue':issue,'diagnosis':diagnosis,'files':files,'feedback':feedback},Patch.model_json_schema()))
    changes={edit.path:edit.content for edit in patch.changes}
    if len(changes)!=len(patch.changes): raise ValueError('Model returned duplicate file edits')
    return {'explanation':patch.explanation,'changes':changes}
