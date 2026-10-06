from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.database import get_db
from app.enums import WorkerStatus
from app.models import Worker


router = APIRouter(tags=["Diagnostics"])


@router.get("/diagnostics")
def diagnostics(db: Session = Depends(get_db)):
    try:
        db.execute(select(func.count()).select_from(Worker))
        total_workers = int(
            db.scalar(select(func.count()).select_from(Worker)) or 0
        )
        online_workers = int(
            db.scalar(
                select(func.count())
                .select_from(Worker)
                .where(Worker.status == WorkerStatus.ONLINE.value)
            )
            or 0
        )
        database = {"status": "ok"}
    except Exception:
        database = {"status": "error"}
        return {
            "status": "degraded",
            "database": database,
            "workers": {
                "online": 0,
                "total": 0,
            },
        }

    return {
        "status": "ok",
        "database": database,
        "workers": {
            "online": online_workers,
            "total": total_workers,
        },
    }
