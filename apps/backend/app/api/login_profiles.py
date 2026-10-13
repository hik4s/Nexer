from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AutomationVersion, LoginProfile, LoginProfileVersion, utcnow
from app.errors import ApiError
from app.schemas_login_profile import LoginConfiguration, LoginProfileCreate, ProfilePublish
from app.repositories.login_profile import find_version

router = APIRouter(prefix="/login-profiles", tags=["Login profiles"])

def require_profile(db, profile_id):
    profile = db.get(LoginProfile, profile_id)
    if not profile: raise ApiError(404, "LOGIN_PROFILE_NOT_FOUND", "Perfil não encontrado.")
    return profile

def read_profile(db, profile, version=None):
    item = find_version(db, profile.id, version or profile.current_version)
    if not item: raise ApiError(404, "LOGIN_PROFILE_VERSION_NOT_FOUND", "Versão não encontrada.")
    from app.models import AccessGroup
    group = db.get(AccessGroup, profile.group_id) if profile.group_id else None
    return {"id": profile.id, "name": profile.name, "group_id": profile.group_id, "group_name": group.name if group else None, "status": profile.status, "current_version": item.version, "configuration": item.configuration, "published": item.published_at is not None}

@router.get("")
def list_profiles(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    items = db.scalars(select(LoginProfile).order_by(LoginProfile.id).offset(offset).limit(limit)).all()
    return {"items": [read_profile(db, item) for item in items], "total": db.scalar(select(func.count()).select_from(LoginProfile)), "limit": limit, "offset": offset}

@router.post("", status_code=201)
def create_profile(payload: LoginProfileCreate, db: Session = Depends(get_db)):
    from app.api.workspace import require_group
    require_group(db, payload.group_id)
    configuration = LoginConfiguration(login_url=payload.login_url)
    if payload.template_profile_id:
        template = require_profile(db, payload.template_profile_id)
        source = find_version(db, template.id, template.current_version).configuration
        # Copy target locations only; confirmation/origins belong to each URL.
        configuration = LoginConfiguration(login_url=payload.login_url, **{key: source.get(key) for key in ("username_target", "password_target", "submit_target")})
    profile = LoginProfile(name=payload.name, group_id=payload.group_id, current_version=1, status="DRAFT")
    db.add(profile); db.flush()
    db.add(LoginProfileVersion(profile_id=profile.id, version=1, configuration=configuration.model_dump()))
    db.commit()
    return read_profile(db, profile)

@router.get("/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    return read_profile(db, require_profile(db, profile_id))

@router.get("/{profile_id}/versions/{version}")
def get_profile_version(profile_id: int, version: int, db: Session = Depends(get_db)):
    return read_profile(db, require_profile(db, profile_id), version)

@router.post("/{profile_id}/versions", status_code=201)
def create_version(profile_id: int, payload: LoginConfiguration, db: Session = Depends(get_db)):
    profile = require_profile(db, profile_id)
    if profile.status == "DISABLED": raise ApiError(409, "LOGIN_PROFILE_DISABLED", "Perfil desativado.")
    latest = db.scalar(select(func.max(LoginProfileVersion.version)).where(LoginProfileVersion.profile_id == profile_id)) or 0
    item = LoginProfileVersion(profile_id=profile_id, version=latest + 1, configuration=payload.model_dump())
    db.add(item); profile.current_version = item.version; profile.status = "DRAFT"
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise ApiError(409, "PROFILE_VERSION_CONFLICT", "Atualize o perfil e tente novamente.") from None
    return read_profile(db, profile)

@router.post("/{profile_id}/publish")
def publish_profile(profile_id: int, payload: ProfilePublish, db: Session = Depends(get_db)):
    profile = require_profile(db, profile_id)
    if profile.status == "DISABLED": raise ApiError(409, "LOGIN_PROFILE_DISABLED", "Perfil desativado.")
    item = find_version(db, profile_id, payload.version)
    if not item: raise ApiError(404, "LOGIN_PROFILE_VERSION_NOT_FOUND", "Versão não encontrada.")
    if any(not item.configuration.get(key) for key in ("username_target", "password_target", "submit_target", "success_rule")):
        raise ApiError(422, "LOGIN_PROFILE_INCOMPLETE", "Identifique os campos e informe uma regra de sucesso.")
    item.published_at = item.published_at or utcnow(); profile.current_version = item.version; profile.status = "READY"
    db.commit(); return read_profile(db, profile)

@router.delete("/{profile_id}/permanent", status_code=204)
def delete_profile_permanently(profile_id: int, db: Session = Depends(get_db)):
    profile = require_profile(db, profile_id)
    if login_recordings.has_active_profile(profile_id):
        raise ApiError(409, "LOGIN_PROFILE_RECORDING_ACTIVE", "Cancele a seleção de campos no Edge antes de excluir este perfil.")
    for recipe in db.scalars(select(AutomationVersion.recipe)):
        reference = recipe.get("login_profile") if isinstance(recipe, dict) else None
        if isinstance(reference, dict) and reference.get("id") == profile_id:
            raise ApiError(409, "LOGIN_PROFILE_IN_USE", "Este perfil está vinculado a uma versão salva de automação. Desative o perfil para preservar essas versões e o histórico.")
    db.execute(delete(LoginProfileVersion).where(LoginProfileVersion.profile_id == profile_id))
    db.delete(profile)
    db.commit()
    return Response(status_code=204)

@router.delete("/{profile_id}")
def disable_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = require_profile(db, profile_id); profile.status = "DISABLED"; db.commit()
    return read_profile(db, profile)


from app.security import SESSION_COOKIE_NAME
from app.services.login_recordings import login_recordings

def recording_error(exc):
    code = str(exc)
    if code == "LOGIN_RECORDING_NOT_FOUND": return ApiError(404, code, "Seleção não encontrada nesta sessão.")
    if code == "CORPORATE_AUTH_NOT_VALIDATED":
        return ApiError(409, code, "A seleção de campos para SGIND/IQOS está bloqueada: a validação corporativa deste recurso ainda está pendente.")
    return ApiError(409, code if code in {"CORPORATE_AUTH_NOT_VALIDATED", "LOGIN_RECORDING_CAPACITY"} else "LOGIN_PICKER_FAILED", "Não foi possível iniciar a seleção dos campos.")

@router.post("/{profile_id}/recordings", status_code=201)
def start_recording(profile_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    profile = require_profile(db, profile_id)
    if profile.status == "DISABLED": raise ApiError(409, "LOGIN_PROFILE_DISABLED", "Perfil desativado.")
    version = find_version(db, profile_id, profile.current_version)
    try: result = login_recordings.start(request.cookies.get(SESSION_COOKIE_NAME), profile_id, version.version, version.configuration)
    except RuntimeError as exc: raise recording_error(exc) from None
    response.headers["Cache-Control"] = "no-store"
    return result

@router.get("/{profile_id}/recordings/{recording_id}")
def get_recording(profile_id: int, recording_id: str, request: Request, response: Response):
    try: result = login_recordings.get(recording_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError as exc: raise recording_error(exc) from None
    if result["profile_id"] != profile_id: raise ApiError(404, "LOGIN_RECORDING_NOT_FOUND", "Seleção não encontrada.")
    response.headers["Cache-Control"] = "no-store"; return result

@router.post("/{profile_id}/recordings/{recording_id}/cancel")
def cancel_recording(profile_id: int, recording_id: str, request: Request, response: Response):
    get_recording(profile_id, recording_id, request, response)
    try: return login_recordings.cancel(recording_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError as exc: raise recording_error(exc) from None
