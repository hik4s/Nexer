from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Destination


def get_by_id(db: Session, destination_id: int):
    return db.get(Destination, destination_id)


def get_by_code(db: Session, code: str):
    return db.scalar(select(Destination).where(Destination.code == code))


def list_items(db: Session, *, offset: int, limit: int):
    total = int(
        db.scalar(select(func.count()).select_from(Destination)) or 0
    )
    items = list(
        db.scalars(
            select(Destination)
            .order_by(Destination.name, Destination.id)
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return items, total
