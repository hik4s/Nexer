from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event


def list_after(
    db: Session,
    *,
    execution_id: int,
    after_id: int,
) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(
                Event.execution_id == execution_id,
                Event.id > after_id,
            )
            .order_by(Event.id)
        ).all()
    )
