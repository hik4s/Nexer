"""Submission orchestration. Credentials never enter SQLAlchemy models."""
from datetime import timedelta

from sqlalchemy import select

from app.models import Worker, utcnow
from app.security import put_session_credentials
from app.worker_channel import worker_channel


def bind_execution_credentials(execution_id, owner, systems, db):
    worker_ids = worker_channel.worker_ids()
    now = utcnow()
    workers = db.scalars(select(Worker).where(Worker.worker_id.in_(worker_ids), Worker.status == "ONLINE", Worker.stopped_at.is_(None), Worker.heartbeat_at >= now - timedelta(seconds=30), Worker.heartbeat_at <= now).order_by(Worker.current_load, Worker.worker_id)).all()
    worker_id = worker_channel.choose_worker([worker.worker_id for worker in workers])
    incarnation = worker_channel.incarnation(worker_id)
    try:
        # Release the session lock before taking the channel lock: resolve takes
        # channel -> session -> vault. A concurrent logout safely revokes this put.
        put_session_credentials(execution_id, owner, systems)
        worker_channel.bind(execution_id, owner, expected_worker_id=worker_id, expected_incarnation=incarnation)
        return worker_id
    except Exception:
        worker_channel.revoke(execution_id)
        raise
