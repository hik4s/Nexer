from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import AutomationStatus
from app.errors import ApiError
from app.models import Automation, AutomationVersion
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


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_recipe_contract(recipe: dict[str, Any]) -> None:
    if recipe.get("schema_version") != 1:
        raise ApiError(422, "INVALID_RECIPE", "Recipe schema_version must be 1")
    if not isinstance(recipe.get("name"), str) or not recipe["name"].strip():
        raise ApiError(422, "INVALID_RECIPE", "Recipe name is required")
    if not isinstance(recipe.get("variables", {}), dict):
        raise ApiError(422, "INVALID_RECIPE", "Recipe variables must be an object")
    if not isinstance(recipe.get("steps"), list) or not recipe["steps"]:
        raise ApiError(422, "INVALID_RECIPE", "Recipe steps are required")
    if not isinstance(recipe.get("output"), dict):
        raise ApiError(422, "INVALID_RECIPE", "Recipe output is required")
    if recipe["output"].get("type") != "file":
        raise ApiError(422, "INVALID_RECIPE", "Recipe output type must be file")


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

    automation.current_version = item.version
    automation.status = AutomationStatus.PUBLISHED.value
    item.published_at = item.published_at or _now()
    db.commit()

    return {
        "version": item.version,
        "published": True,
        "automation_status": automation.status,
    }
