from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import AutomationStatus
from app.errors import ApiError
from app.models import Automation
from app.repositories.automation import (
    get_by_code,
    get_by_id,
    list_automations,
)
from app.schemas import AutomationCreate, AutomationListResponse, AutomationRead


router = APIRouter(prefix="/automations", tags=["Automations"])


@router.post("", response_model=AutomationRead, status_code=201)
def create_automation(payload: AutomationCreate, db: Session = Depends(get_db)):
    if get_by_code(db, payload.code) is not None:
        raise ApiError(
            status_code=409,
            code="AUTOMATION_CODE_EXISTS",
            message="Automation code already exists",
        )

    automation = Automation(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        system=payload.system,
        status=AutomationStatus.DRAFT.value,
    )
    db.add(automation)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="AUTOMATION_CODE_EXISTS",
            message="Automation code already exists",
        ) from exc

    db.refresh(automation)
    return automation


@router.get("", response_model=AutomationListResponse)
def list_automation_items(
    status: AutomationStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = list_automations(
        db,
        offset=offset,
        limit=limit,
        status=status,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{automation_id}", response_model=AutomationRead)
def get_automation(automation_id: int, db: Session = Depends(get_db)):
    automation = get_by_id(db, automation_id)
    if automation is None:
        raise ApiError(
            status_code=404,
            code="AUTOMATION_NOT_FOUND",
            message="Automation not found",
        )
    return automation
