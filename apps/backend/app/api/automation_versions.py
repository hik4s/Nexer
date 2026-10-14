from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, Request
from pydantic import BaseModel, Field
from app.services.report_options import ReportOptionsError, read_options
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from recipe import RecipeValidationError, validate_recipe
from app.enums import AutomationStatus
from app.errors import ApiError
from app.models import Automation, AutomationVersion
from app.services.profile_execution import profile_configuration, validate_profile_reference
from app.schemas_execution import CorporateCredential
from app.security import SESSION_COOKIE_NAME, resolve_session
from browser_manager import BrowserManager
from login_profiles import authenticate_profile
from app.repositories.automation_version import get_by_id, list_versions, next_version
from app.schemas_version import (
    AutomationVersionCreate,
    AutomationVersionListResponse,
    AutomationVersionPublishResponse,
    AutomationVersionRead,
    AutomationVersionTestResponse,
)


router = APIRouter(
    prefix="/automations/{automation_id}/versions",
    tags=["Automation Versions"],
)


class ReportOptionsRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    profile_credentials: dict[str, CorporateCredential] = Field(default_factory=dict, repr=False, max_length=20)


@router.post("/{version}/input-options")
def get_input_options(automation_id: int, version: int, payload: ReportOptionsRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")
    item = get_by_id(db, automation_id, version)
    if item is None:
        raise ApiError(404, "AUTOMATION_VERSION_NOT_FOUND", "Automation version not found")
    if automation.status != "PUBLISHED" or automation.current_version != version:
        raise ApiError(409, "REPORT_NOT_PUBLISHED", "Publique o relatório antes de preparar os filtros.")
    if automation.system in {"SGIND", "IQOS"}:
        raise ApiError(409, "CORPORATE_AUTH_NOT_VALIDATED", "Carregamento corporativo aguarda validação no ambiente autorizado.")
    _validate_recipe_contract(item.recipe)
    page_factory = None
    values = {}
    if item.recipe.get("login_profile"):
        identity, configuration = profile_configuration(db, item.recipe["login_profile"])
        if set(payload.profile_credentials) != {identity}:
            raise ApiError(422, "PROFILE_CREDENTIALS_REQUIRED", "Informe as credenciais para consultar as opções deste site.")
        credential = payload.profile_credentials[identity]
        values = {"username": credential.username.get_secret_value(), "password": credential.password.get_secret_value()}
        owner = request.cookies.get(SESSION_COOKIE_NAME)
        def authorize():
            if resolve_session(owner) is None: raise RuntimeError("CREDENTIALS_UNAVAILABLE")
        def page_factory():
            page = BrowserManager(headless=True).create_monitored_login_page(configuration, authorize=authorize, accept_downloads=False)
            try:
                authenticate_profile(page, configuration, values, cancellation_requested=lambda: resolve_session(owner) is None)
                page.corporate_policy.allowed_methods = {"GET", "HEAD"}
                return page
            except Exception:
                page.close(); raise ReportOptionsError("OPTIONS_PAGE_UNAVAILABLE") from None
    elif payload.profile_credentials:
        raise ApiError(422, "PROFILE_CREDENTIALS_MISMATCH", "Este fluxo não usa o perfil informado.")
    try:
        result = read_options(item.recipe, payload.inputs, page_factory=page_factory) if page_factory else read_options(item.recipe, payload.inputs)
    except ReportOptionsError as exc:
        raise ApiError(422, str(exc), "Não foi possível carregar as opções. Confira o endereço e os filtros da página local.") from None
    finally:
        values.clear()
    response.headers["Cache-Control"] = "no-store"
    return result


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_recipe_contract(recipe: dict[str, Any]) -> None:
    try:
        validate_recipe(recipe)
    except RecipeValidationError:
        raise ApiError(422, "INVALID_RECIPE", "Receita incompatível com o runtime.") from None


def _to_read(automation: Automation, version: AutomationVersion) -> AutomationVersionRead:
    return AutomationVersionRead(
        id=version.id,
        automation_id=version.automation_id,
        version=version.version,
        recipe=version.recipe,
        created_at=version.created_at,
        created_by=version.created_by,
        test_status=version.test_status,
        published=(
            automation.status == AutomationStatus.PUBLISHED.value
            and automation.current_version == version.version
        ),
        published_at=version.published_at,
    )


@router.post("", response_model=AutomationVersionRead, status_code=201)
def create_version(
    automation_id: int,
    payload: AutomationVersionCreate,
    db: Session = Depends(get_db),
):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")

    version = AutomationVersion(
        automation_id=automation_id,
        version=next_version(db, automation_id),
        recipe=payload.recipe,
        created_by=payload.created_by,
        created_at=_now(),
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "AUTOMATION_VERSION_CONFLICT",
            "Automation version could not be created",
        ) from exc

    db.refresh(version)
    return _to_read(automation, version)


@router.get("", response_model=AutomationVersionListResponse)
def list_version_items(
    automation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")

    items, total = list_versions(db, automation_id, offset=offset, limit=limit)
    return {
        "items": [_to_read(automation, item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{version}", response_model=AutomationVersionRead)
def get_version(automation_id: int, version: int, db: Session = Depends(get_db)):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")

    item = get_by_id(db, automation_id, version)
    if item is None:
        raise ApiError(404, "AUTOMATION_VERSION_NOT_FOUND", "Automation version not found")

    return _to_read(automation, item)


@router.post("/{version}/test", response_model=AutomationVersionTestResponse)
def test_version(automation_id: int, version: int, db: Session = Depends(get_db)):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")

    item = get_by_id(db, automation_id, version)
    if item is None:
        raise ApiError(404, "AUTOMATION_VERSION_NOT_FOUND", "Automation version not found")

    try:
        _validate_recipe_contract(item.recipe)
    except ApiError:
        item.test_status = "FAILED"
        db.commit()
        raise

    item.test_status = "PASSED"
    db.commit()
    return {
        "version": item.version,
        "test_status": item.test_status,
        "automation_status": automation.status,
    }


@router.post("/{version}/publish", response_model=AutomationVersionPublishResponse)
def publish_version(automation_id: int, version: int, db: Session = Depends(get_db)):
    automation = db.get(Automation, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Automation not found")

    item = get_by_id(db, automation_id, version)
    if item is None:
        raise ApiError(404, "AUTOMATION_VERSION_NOT_FOUND", "Automation version not found")

    if item.test_status != "PASSED":
        raise ApiError(
            409,
            "AUTOMATION_VERSION_NOT_TESTED",
            "Automation version must pass its test before publishing",
        )

    _validate_recipe_contract(item.recipe)
    if item.recipe.get("login_profile"):
        validate_profile_reference(db, item.recipe["login_profile"])
    automation.current_version = item.version
    automation.status = AutomationStatus.PUBLISHED.value
    item.published_at = item.published_at or _now()
    db.commit()

    return {
        "version": item.version,
        "published": True,
        "automation_status": automation.status,
    }
