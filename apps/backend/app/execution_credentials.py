"""Submission orchestration. Credentials never enter SQLAlchemy models."""
from datetime import timedelta

from sqlalchemy import select

from app.models import Worker, utcnow
from app.security import put_session_credentials
from app.worker_channel import worker_channel


def bind_execution_credentials(execution_id, owner, systems, db):
    worker_id = worker_channel.current_worker_id()
    worker = db.scalar(select(Worker).where(Worker.worker_id == worker_id))
    now = utcnow()
    if (worker is None or worker.status != "ONLINE" or worker.stopped_at is not None
        or not now - timedelta(seconds=30) <= worker.heartbeat_at <= now):
        raise RuntimeError("CREDENTIALS_UNAVAILABLE")
    try:
        # Release the session lock before taking the channel lock: resolve takes
        # channel -> session -> vault. A concurrent logout safely revokes this put.
        put_session_credentials(execution_id, owner, systems)
        worker_channel.bind(execution_id, owner, expected_worker_id=worker_id)
    except Exception:
        worker_channel.revoke(execution_id)
        raise
