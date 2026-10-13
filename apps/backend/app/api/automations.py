from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Execution, ExecutionAutomation, Routine
from app.services.history_deletion import TERMINAL_STATUSES

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


@router.delete("/{automation_id}")
def remove_automation(automation_id: int, db: Session = Depends(get_db)):
    automation = get_by_id(db, automation_id)
    if automation is None:
        raise ApiError(404, "AUTOMATION_NOT_FOUND", "Fluxo não encontrado.")
    in_flight = db.scalar(
        select(Execution.id).join(ExecutionAutomation, ExecutionAutomation.execution_id == Execution.id)
        .where(ExecutionAutomation.automation_id == automation_id,
               Execution.status.not_in(TERMINAL_STATUSES)).limit(1)
    )
    if in_flight is not None:
        raise ApiError(409, "AUTOMATION_IN_USE", "Aguarde ou cancele as execuções deste fluxo antes de removê-lo.")
    has_history = db.scalar(select(ExecutionAutomation.id).where(
        ExecutionAutomation.automation_id == automation_id).limit(1)) is not None
    # Routine entries are JSON, not foreign keys: preserve them and block future runs.
    used_by_routine = any(
        item.get("automation_id") == automation_id
        for routine in db.scalars(select(Routine)).all()
        for item in routine.items if isinstance(item, dict)
    )
    if has_history or used_by_routine:
        automation.status = AutomationStatus.ARCHIVED.value
        db.commit()
        return {"archived": True}
    db.delete(automation)  # ORM cascade deletes unused recipe versions.
    db.commit()
    return {"archived": False}


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
