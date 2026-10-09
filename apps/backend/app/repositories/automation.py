from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import AutomationStatus
from app.models import Automation


def get_by_id(db: Session, automation_id: int) -> Automation | None:
    return db.get(Automation, automation_id)


def get_by_code(db: Session, code: str) -> Automation | None:
    return db.scalar(select(Automation).where(Automation.code == code))


def list_automations(
    db: Session,
    *,
    offset: int,
    limit: int,
    status: AutomationStatus | None = None,
) -> tuple[list[Automation], int]:
    base = select(Automation)
    count = select(func.count()).select_from(Automation)

    if status is not None:
        base = base.where(Automation.status == status.value)
        count = count.where(Automation.status == status.value)

    total = int(db.scalar(count) or 0)
    items = list(
        db.scalars(
            base.order_by(Automation.id).offset(offset).limit(limit)
        ).all()
    )
    return items, total
