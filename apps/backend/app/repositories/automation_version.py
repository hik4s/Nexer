from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AutomationVersion


def get_by_id(db: Session, automation_id: int, version: int) -> AutomationVersion | None:
    return db.scalar(
        select(AutomationVersion).where(
            AutomationVersion.automation_id == automation_id,
            AutomationVersion.version == version,
        )
    )


def next_version(db: Session, automation_id: int) -> int:
    current = db.scalar(
        select(func.max(AutomationVersion.version)).where(
            AutomationVersion.automation_id == automation_id
        )
    )
    return int(current or 0) + 1


def list_versions(db: Session, automation_id: int, *, offset: int, limit: int):
    count = select(func.count()).select_from(AutomationVersion).where(
        AutomationVersion.automation_id == automation_id
    )
    total = int(db.scalar(count) or 0)
    items = list(
        db.scalars(
            select(AutomationVersion)
            .where(AutomationVersion.automation_id == automation_id)
            .order_by(AutomationVersion.version.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return items, total
