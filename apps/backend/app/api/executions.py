from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import (
    AutomationStatus,
    ExecutionAutomationStatus,
    ExecutionStage,
    ExecutionStatus,
)
from app.errors import ApiError
from app.models import Automation, AutomationVersion, Execution, ExecutionAutomation, utcnow
from app.repositories.execution import get_by_id, get_items, list_executions
from app.schemas_execution import (
    ExecutionAutomationRead,
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionRead,
)

_CREDENTIAL_REF_KEYS = {"credential_ref"}


def _validate_secret_inputs(payload_inputs: dict, recipe: dict) -> None:
    declarations = recipe.get("variables", {})
    if not isinstance(declarations, dict):
        return

    for name, declaration in declarations.items():
        if not isinstance(declaration, dict) or not declaration.get("secret"):
            continue
        if name not in payload_inputs:
            continue

        value = payload_inputs[name]
        if (
            not isinstance(value, dict)
            or set(value.keys()) != _CREDENTIAL_REF_KEYS
            or not isinstance(value.get("credential_ref"), str)
            or not value["credential_ref"].strip()
        ):
            raise ApiError(
                422,
                "SECRET_INPUT_FORBIDDEN",
                "Secret execution inputs must use a credential reference",
            )



router = APIRouter(prefix="/executions", tags=["Executions"])


def _to_read(execution: Execution, items: list[ExecutionAutomation]) -> ExecutionRead:
    return ExecutionRead(
        id=execution.id,
        name=execution.name,
        requested_by=execution.requested_by,
        period_start=execution.period_start,
        period_end=execution.period_end,
        status=execution.status,
        send_to_network=execution.send_to_network,
        keep_local_copy=execution.keep_local_copy,
        overwrite_existing=execution.overwrite_existing,
        test_mode=execution.test_mode,
        inputs=execution.inputs,
        created_at=execution.created_at,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        cancel_requested=execution.cancel_requested,
        items=[
            ExecutionAutomationRead(
                id=item.id,
                execution_id=item.execution_id,
                automation_id=item.automation_id,
                automation_version=item.automation_version,
                status=item.status,
                stage=item.stage,
                attempts=item.attempts,
                last_progress_at=item.last_progress_at,
                started_at=item.started_at,
                finished_at=item.finished_at,
                error_type=item.error_type,
                error_detail=item.error_detail,
            )
            for item in items
        ],
    )


@router.post("", response_model=ExecutionRead, status_code=201)
def create_execution(payload: ExecutionCreate, db: Session = Depends(get_db)):
    automations = db.scalars(
        select(Automation).where(Automation.id.in_(payload.automation_ids))
    ).all()
    by_id = {automation.id: automation for automation in automations}

    missing = [item for item in payload.automation_ids if item not in by_id]
    if missing:
        raise ApiError(
            404,
            "AUTOMATION_NOT_FOUND",
            "Automation not found",
            {"ids": missing},
        )

    versions: dict[int, int] = {}
    for automation_id in payload.automation_ids:
        automation = by_id[automation_id]
        if automation.status != AutomationStatus.PUBLISHED.value:
            raise ApiError(
                409,
                "AUTOMATION_NOT_PUBLISHED",
                "Automation is not published",
            )
        if automation.current_version is None:
            raise ApiError(
                409,
                "AUTOMATION_VERSION_NOT_FOUND",
                "Published automation has no current version",
            )

        version = db.scalar(
            select(AutomationVersion).where(
                AutomationVersion.automation_id == automation.id,
                AutomationVersion.version == automation.current_version,
            )
        )
        if version is None:
            raise ApiError(
                409,
                "AUTOMATION_VERSION_NOT_FOUND",
                "Automation current version is missing",
            )
        _validate_secret_inputs(payload.inputs, version.recipe)
        versions[automation.id] = version.version

    execution = Execution(
        name=payload.name,
        requested_by=payload.requested_by,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=ExecutionStatus.QUEUED.value,
        send_to_network=payload.send_to_network,
        keep_local_copy=payload.keep_local_copy,
        overwrite_existing=payload.overwrite_existing,
        test_mode=payload.test_mode,
        inputs=payload.inputs,
        created_at=utcnow(),
        cancel_requested=False,
    )
    db.add(execution)
    try:
        db.flush()
        for automation_id in payload.automation_ids:
            db.add(
                ExecutionAutomation(
                    execution_id=execution.id,
                    automation_id=automation_id,
                    automation_version=versions[automation_id],
                    status=ExecutionAutomationStatus.PENDING.value,
                    stage=ExecutionStage.CREATED.value,
                    attempts=0,
                )
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            409,
            "EXECUTION_CREATE_CONFLICT",
            "Execution could not be created",
        ) from exc

    db.refresh(execution)
    return _to_read(execution, get_items(db, execution.id))


@router.get("", response_model=ExecutionListResponse)
def list_execution_items(
    status: ExecutionStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = list_executions(
        db,
        offset=offset,
        limit=limit,
        status=status,
    )
    return {
        "items": [_to_read(item, get_items(db, item.id)) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{execution_id}", response_model=ExecutionRead)
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    execution = get_by_id(db, execution_id)
    if execution is None:
        raise ApiError(404, "EXECUTION_NOT_FOUND", "Execution not found")
    return _to_read(execution, get_items(db, execution.id))


@router.post("/{execution_id}/cancel", response_model=ExecutionRead)
def cancel_execution(execution_id: int, db: Session = Depends(get_db)):
    execution = get_by_id(db, execution_id)
    if execution is None:
        raise ApiError(404, "EXECUTION_NOT_FOUND", "Execution not found")

    if execution.status in {
        ExecutionStatus.SUCCEEDED.value,
        ExecutionStatus.PARTIAL.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.CANCELLED.value,
    }:
        raise ApiError(
            409,
            "EXECUTION_ALREADY_TERMINAL",
            "Execution is already in a terminal state",
        )

    execution.cancel_requested = True
    items = get_items(db, execution.id)
    now = utcnow()

    if execution.status == ExecutionStatus.QUEUED.value:
        execution.status = ExecutionStatus.CANCELLED.value
        execution.finished_at = now
        for item in items:
            item.status = ExecutionAutomationStatus.CANCELLED.value
            item.stage = ExecutionStage.CANCELLED.value
            item.finished_at = now
        db.add(
            __import__("app.models", fromlist=["Event"]).Event(
                execution_id=execution.id,
                type="execution.cancelled",
                level="INFO",
                message="execution cancelled before worker claim",
                payload={"reason": "API_REQUEST"},
                created_at=now,
            )
        )
    else:
        db.add(
            __import__("app.models", fromlist=["Event"]).Event(
                execution_id=execution.id,
                type="execution.cancel_requested",
                level="INFO",
                message="execution cancellation requested",
                payload={"reason": "API_REQUEST"},
                created_at=now,
            )
        )

    db.commit()
    db.refresh(execution)
    return _to_read(execution, get_items(db, execution.id))
