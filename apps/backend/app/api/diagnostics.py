from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.database import get_db
from app.enums import WorkerStatus
from app.models import AutomationVersion, Worker


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
        authentication = _authentication_diagnostics(db)
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
            "authentication": {
                "configured": 0,
                "renewal_configured": 0,
            },
        }

    return {
        "status": "ok",
        "database": database,
        "workers": {
            "online": online_workers,
            "total": total_workers,
        },
        "authentication": authentication,
    }


def _authentication_diagnostics(db: Session) -> dict[str, int]:
    configured = 0
    renewal_configured = 0

    for recipe in db.scalars(select(AutomationVersion.recipe)).all():
        if not isinstance(recipe, dict):
            continue
        authentication = recipe.get("authentication")
        if not isinstance(authentication, dict):
            continue
        configured += 1
        if isinstance(authentication.get("renewal"), dict):
            renewal_configured += 1

    return {
        "configured": configured,
        "renewal_configured": renewal_configured,
    }
