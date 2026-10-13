from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ExecutionStatus
from app.models import Execution, ExecutionAutomation


def get_by_id(db: Session, execution_id: int) -> Execution | None:
    return db.get(Execution, execution_id)


def get_items(db: Session, execution_id: int) -> list[ExecutionAutomation]:
    return list(
        db.scalars(
            select(ExecutionAutomation)
            .where(ExecutionAutomation.execution_id == execution_id)
            .order_by(ExecutionAutomation.id)
        ).all()
    )


def list_executions(
    db: Session,
    *,
    offset: int,
    limit: int,
    status: ExecutionStatus | None = None,
) -> tuple[list[Execution], int]:
    base = select(Execution)
    count = select(func.count()).select_from(Execution)

    if status is not None:
        base = base.where(Execution.status == status.value)
        count = count.where(Execution.status == status.value)

    total = int(db.scalar(count) or 0)
    items = list(
        db.scalars(
            base.order_by(Execution.id).offset(offset).limit(limit)
        ).all()
    )
    return items, total
