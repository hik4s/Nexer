import hashlib
import json
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from app.database import get_db
from app.errors import ApiError
from app.models import Automation, AutomationVersion, Execution, ExecutionBatch
from app.services.history_deletion import TERMINAL_STATUSES, delete_finished_executions
from app.schemas_batch import BatchCreate
from app.schemas_execution import ExecutionCreate
from app.security import SESSION_COOKIE_NAME
from app.worker_channel import worker_channel
from app.api.executions import prepare_execution, request_execution_cancel, _to_read
from app.repositories.execution import get_items
from login_profiles import profile_key
from recipe import validate_recipe, RecipeValidationError
from resolver import VariableResolver, VariableResolutionError

router = APIRouter(prefix="/execution-batches", tags=["Execution batches"])
TERMINAL = {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"}

def batch_status(executions):
    statuses = {item.status for item in executions}
    if statuses == {"SUCCEEDED"}: return "SUCCEEDED"
    if statuses == {"FAILED"}: return "FAILED"
    if statuses == {"CANCELLED"}: return "CANCELLED"
    if any(item.cancel_requested and item.status not in TERMINAL for item in executions): return "CANCEL_REQUESTED"
    if statuses <= TERMINAL: return "PARTIAL"
    if statuses == {"QUEUED"}: return "QUEUED"
    return "RUNNING"

def read_batch(db, batch):
    executions = db.scalars(select(Execution).where(Execution.batch_id == batch.id).order_by(Execution.id)).all()
    return {"id": batch.id, "name": batch.name, "created_at": batch.created_at, "status": batch_status(executions),
        "executions": [_to_read(item, get_items(db, item.id)).model_dump() for item in executions]}

def require_batch(db, batch_id):
    batch = db.get(ExecutionBatch, batch_id)
    if not batch: raise ApiError(404, "BATCH_NOT_FOUND", "Lote não encontrado.")
    return batch

@router.get("")
def list_batches(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    batches = db.scalars(select(ExecutionBatch).order_by(ExecutionBatch.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [read_batch(db, batch) for batch in batches], "total": db.scalar(select(func.count()).select_from(ExecutionBatch)), "limit": limit, "offset": offset}

@router.get("/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    return read_batch(db, require_batch(db, batch_id))

@router.post("", status_code=201)
def create_batch(payload: BatchCreate, request: Request, db: Session = Depends(get_db)):
    owner_key = hashlib.sha256(request.cookies[SESSION_COOKIE_NAME].encode()).hexdigest()
    # Fingerprint configuration only: never hash or persist credential material.
    fingerprint = hashlib.sha256(json.dumps(payload.model_dump(mode="json", exclude={"profile_credentials"}), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    created_ids = []
    try:
        db.execute(text("BEGIN IMMEDIATE"))
        existing = db.scalar(select(ExecutionBatch).where(ExecutionBatch.owner_key == owner_key, ExecutionBatch.idempotency_key == payload.idempotency_key))
        if existing:
            if existing.fingerprint != fingerprint: raise ApiError(409, "BATCH_IDEMPOTENCY_CONFLICT", "Este identificador já foi usado para outro lote.")
            result = read_batch(db, existing); db.commit(); return result
        preparations = []
        used_profiles = set()
        for item in payload.items:
            automation = db.get(Automation, item.automation_id)
            if not automation: raise ApiError(404, "AUTOMATION_NOT_FOUND", "Fluxo não encontrado.")
            if automation.status != "PUBLISHED" or automation.current_version != item.version: raise ApiError(409, "BATCH_VERSION_CHANGED", "Atualize a seleção dos fluxos antes de iniciar o lote.")
            if automation.system in {"SGIND", "IQOS"}: raise ApiError(409, "CORPORATE_AUTH_NOT_VALIDATED", "O lote contém um fluxo corporativo ainda não validado.")
            version = db.scalar(select(AutomationVersion).where(AutomationVersion.automation_id == automation.id, AutomationVersion.version == item.version))
            if version is None: raise ApiError(409, "AUTOMATION_VERSION_NOT_FOUND", "Versão do fluxo não encontrada.")
            try:
                recipe = validate_recipe(version.recipe)
                values = dict(item.inputs)
                if item.period_start: values["period_start"] = item.period_start.strftime("%Y-%m-%d")
                if item.period_end: values["period_end"] = item.period_end.strftime("%Y-%m-%d")
                resolver = VariableResolver(declarations=recipe.get("variables", {}), values=values)
                resolver.validate_required()
                for name, declaration in recipe.get("variables", {}).items():
                    if declaration.get("secret"): raise ValueError()
                    if name in values: resolver.resolve("{{" + name + "}}")
            except (RecipeValidationError, VariableResolutionError, ValueError):
                raise ApiError(422, "BATCH_INPUT_INVALID", "Revise os parâmetros obrigatórios e seus tipos em cada fluxo.") from None
            reference = recipe.get("login_profile")
            identity = profile_key(reference["id"], reference["version"]) if reference else None
            if identity: used_profiles.add(identity)
            credentials = {identity: payload.profile_credentials[identity]} if identity in payload.profile_credentials and not item.test_mode else {}
            execution = ExecutionCreate(name=(payload.name + " — " + automation.name)[:200], automation_ids=[automation.id], inputs=item.inputs, period_start=item.period_start, period_end=item.period_end, test_mode=item.test_mode, keep_local_copy=item.keep_local_copy, send_to_network=item.send_to_network, overwrite_existing=item.overwrite_existing, profile_credentials=credentials)
            preparations.append(execution)
        if set(payload.profile_credentials) - used_profiles: raise ApiError(422, "PROFILE_CREDENTIALS_MISMATCH", "As credenciais não correspondem aos perfis do lote.")
        batch = ExecutionBatch(name=payload.name, owner_key=owner_key, idempotency_key=payload.idempotency_key, fingerprint=fingerprint)
        db.add(batch); db.flush()
        for execution in preparations:
            created = prepare_execution(execution, request, db, commit=False)
            created_ids.append(created.id)
            db.get(Execution, created.id).batch_id = batch.id
        db.commit()
        return read_batch(db, batch)
    except Exception:
        for execution_id in created_ids: worker_channel.revoke(execution_id)
        db.rollback(); raise

@router.delete("/{batch_id}", status_code=204)
def delete_batch(batch_id: int, request: Request, db: Session = Depends(get_db)):
    batch = require_batch(db, batch_id)
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie or hashlib.sha256(cookie.encode()).hexdigest() != batch.owner_key:
        raise ApiError(404, "BATCH_NOT_FOUND", "Lote não encontrado nesta sessão.")
    executions = db.scalars(select(Execution).where(Execution.batch_id == batch.id)).all()
    if any(execution.status not in TERMINAL_STATUSES for execution in executions):
        raise ApiError(409, "BATCH_NOT_TERMINAL", "Cancele e aguarde todos os fluxos do lote antes de excluir.")
    delete_finished_executions(db, executions)
    db.delete(batch)
    db.commit()
    return Response(status_code=204)


@router.post("/{batch_id}/cancel")
def cancel_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = require_batch(db, batch_id)
    executions = db.scalars(select(Execution).where(Execution.batch_id == batch.id)).all()
    for execution in executions:
        if execution.status not in TERMINAL: request_execution_cancel(execution.id, db, commit=False)
    db.commit(); return read_batch(db, batch)
