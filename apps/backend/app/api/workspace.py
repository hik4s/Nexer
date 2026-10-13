import json
from fastapi import APIRouter, Depends, Response, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AccessGroup, Routine, Automation, AutomationVersion, LoginProfile
from app.errors import ApiError
from recipe import validate_recipe, RecipeValidationError
from resolver import VariableResolver, VariableResolutionError

router = APIRouter(tags=["Workspace"])
from app.services.flow_recordings import flow_recordings
from app.security import SESSION_COOKIE_NAME
class RecordingStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)
@router.post("/flow-recordings", status_code=201)
def start_recording(payload: RecordingStart, request: Request, response: Response):
    try: result = flow_recordings.start_flow(request.cookies.get(SESSION_COOKIE_NAME), payload.url)
    except (RuntimeError, ValueError): raise ApiError(409, "FLOW_RECORDING_UNAVAILABLE", "Informe uma página HTTPS ou HTTP local, sem credenciais ou parâmetros, com uma rota segura. Verifique se há outra gravação aberta.") from None
    response.headers["Cache-Control"] = "no-store"; return result
@router.get("/flow-recordings/{recording_id}")
def get_recording(recording_id: str, request: Request, response: Response):
    try: result = flow_recordings.get(recording_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError: raise ApiError(404, "FLOW_RECORDING_NOT_FOUND", "Gravação não encontrada nesta sessão.") from None
    response.headers["Cache-Control"] = "no-store"; return result
@router.post("/flow-recordings/{recording_id}/{action}")
def control_recording(recording_id: str, action: str, request: Request, response: Response):
    get_recording(recording_id, request, response)
    if action not in {"finish", "cancel"}: raise ApiError(404, "FLOW_RECORDING_ACTION_INVALID", "Ação não encontrada.")
    try: return (flow_recordings.finish if action == "finish" else flow_recordings.cancel)(recording_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError as failure:
        message = "Conclua o login no Edge, abra a rota configurada e clique em Iniciar gravação antes de concluir." if str(failure) == "FLOW_RECORDING_PREPARING" else "Não foi possível concluir a gravação. Verifique a janela do Edge e tente novamente."
        raise ApiError(409, "FLOW_RECORDING_FAILED", message) from None
class Named(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    @field_validator("name")
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError("NAME_REQUIRED")
        return value.strip()
class GroupLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: int | None = Field(default=None, ge=1)
class FavoriteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    automation_id: int = Field(ge=1)
    version: int = Field(ge=1)
    inputs: dict = Field(default_factory=dict)
class FavoriteCreate(Named):
    items: list[FavoriteItem] = Field(min_length=1, max_length=20)
def read_group(group): return {"id": group.id, "name": group.name}
def read_routine(item): return {"id": item.id, "name": item.name, "items": item.items}
def require_group(db, identity):
    if identity is not None and db.get(AccessGroup, identity) is None: raise ApiError(404, "ACCESS_GROUP_NOT_FOUND", "Grupo de acesso não encontrado.")

@router.get("/access-groups")
def groups(db: Session = Depends(get_db)):
    return {"items": [read_group(item) for item in db.scalars(select(AccessGroup).order_by(AccessGroup.name)).all()]}
@router.post("/access-groups", status_code=201)
def create_group(payload: Named, db: Session = Depends(get_db)):
    item = AccessGroup(name=payload.name); db.add(item); db.commit(); return read_group(item)
@router.delete("/access-groups/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(AccessGroup, group_id)
    if not group: raise ApiError(404, "ACCESS_GROUP_NOT_FOUND", "Grupo não encontrado.")
    if db.scalar(select(LoginProfile.id).where(LoginProfile.group_id == group_id).limit(1)) is not None:
        raise ApiError(409, "ACCESS_GROUP_IN_USE", "Desvincule os perfis deste grupo antes de excluir.")
    db.delete(group); db.commit()
    return Response(status_code=204)

@router.put("/login-profiles/{profile_id}/group")
def link_group(profile_id: int, payload: GroupLink, db: Session = Depends(get_db)):
    item = db.get(LoginProfile, profile_id)
    if not item: raise ApiError(404, "LOGIN_PROFILE_NOT_FOUND", "Perfil não encontrado.")
    require_group(db, payload.group_id); item.group_id = payload.group_id; db.commit()
    from app.api.login_profiles import read_profile
    return read_profile(db, item)
@router.get("/routines")
def routines(db: Session = Depends(get_db)):
    return {"items": [read_routine(item) for item in db.scalars(select(Routine).order_by(Routine.id.desc())).all()]}
@router.get("/routines/{routine_id}")
def get_routine(routine_id: int, db: Session = Depends(get_db)):
    item = db.get(Routine, routine_id)
    if not item: raise ApiError(404, "ROUTINE_NOT_FOUND", "Rotina não encontrada.")
    return read_routine(item)
@router.post("/routines", status_code=201)
def create_routine(payload: FavoriteCreate, db: Session = Depends(get_db)):
    if len({item.automation_id for item in payload.items}) != len(payload.items): raise ApiError(422, "ROUTINE_DUPLICATE_FLOW", "Selecione cada fluxo uma única vez.")
    for item in payload.items:
        automation = db.get(Automation, item.automation_id)
        version = db.scalar(select(AutomationVersion).where(AutomationVersion.automation_id == item.automation_id, AutomationVersion.version == item.version))
        if not automation or automation.status != "PUBLISHED" or not version or version.test_status != "PASSED" or (automation.current_version != item.version and version.published_at is None): raise ApiError(409, "ROUTINE_FLOW_UNAVAILABLE", "Use versões publicadas de fluxos disponíveis.")
        try:
            recipe = validate_recipe(version.recipe); declarations = recipe.get("variables", {})
            if len(json.dumps(item.inputs)) > 65536: raise ValueError()
            for name in item.inputs:
                if name not in declarations or declarations[name].get("secret") or name.lower() in {"password", "senha", "username", "token", "credentials", "profile_credentials", "corporate_credentials"}: raise ValueError()
                VariableResolver(declarations=declarations, values=item.inputs).resolve("{{" + name + "}}")
        except (ValueError, RecipeValidationError, VariableResolutionError): raise ApiError(422, "ROUTINE_INPUT_INVALID", "Salve somente parâmetros declarados não secretos.") from None
    routine = Routine(name=payload.name, items=[item.model_dump() for item in payload.items]); db.add(routine); db.commit(); return read_routine(routine)
@router.delete("/routines/{routine_id}", status_code=204)
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    item = db.get(Routine, routine_id)
    if not item: raise ApiError(404, "ROUTINE_NOT_FOUND", "Rotina não encontrada.")
    db.delete(item); db.commit(); return Response(status_code=204)
