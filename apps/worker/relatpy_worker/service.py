from datetime import datetime, timezone
import socket

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.enums import ExecutionStage, ExecutionStatus, WorkerStatus
from app.models import Event, Execution, Worker


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WorkerNotRegisteredError(RuntimeError):
    """Raised when a worker operation requires prior registration."""


class WorkerService:
    def __init__(
        self,
        *,
        session_factory,
        worker_id: str,
        concurrency_limit: int = 1,
        hostname: str | None = None,
        pid: int | None = None,
    ):
        if not worker_id or len(worker_id) > 100:
            raise ValueError("worker_id must contain 1-100 characters")
        if concurrency_limit < 1:
            raise ValueError("concurrency_limit must be >= 1")

        self.session_factory = session_factory
        self.worker_id = worker_id
        self.concurrency_limit = concurrency_limit
        self.hostname = hostname or socket.gethostname()
        self.pid = pid

    def register(self) -> Worker:
        now = utcnow()
        db = self.session_factory()
        try:
            worker = db.scalar(
                select(Worker).where(Worker.worker_id == self.worker_id)
            )
            if worker is None:
                worker = Worker(
                    worker_id=self.worker_id,
                    status=WorkerStatus.ONLINE.value,
                    hostname=self.hostname,
                    pid=self.pid,
                    concurrency_limit=self.concurrency_limit,
                    current_load=0,
                    heartbeat_at=now,
                    started_at=now,
                    stopped_at=None,
                    created_at=now,
                )
                db.add(worker)
            else:
                worker.status = WorkerStatus.ONLINE.value
                worker.hostname = self.hostname
                worker.pid = self.pid
                worker.concurrency_limit = self.concurrency_limit
                worker.current_load = 0
                worker.heartbeat_at = now
                worker.started_at = now
                worker.stopped_at = None
            db.commit()
            db.refresh(worker)
            return worker
        finally:
            db.close()

    def heartbeat(self) -> Worker:
        return self._update_worker_heartbeat()

    def stop(self) -> None:
        now = utcnow()
        db = self.session_factory()
        try:
            worker = self._get_worker(db)
            worker.status = WorkerStatus.OFFLINE.value
            worker.heartbeat_at = now
            worker.stopped_at = now
            worker.current_load = 0
            db.commit()
        finally:
            db.close()

    def claim_next(self) -> int | None:
        db = self.session_factory()
        try:
            db.execute(text("BEGIN IMMEDIATE"))
            worker = self._get_worker(db)

            if worker.status != WorkerStatus.ONLINE.value:
                raise WorkerNotRegisteredError(
                    f"Worker {self.worker_id!r} is not online"
                )
            if worker.current_load >= worker.concurrency_limit:
                db.commit()
                return None

            execution = db.scalar(
                select(Execution)
                .where(
                    Execution.status == ExecutionStatus.QUEUED.value,
                    Execution.cancel_requested.is_(False),
                )
                .order_by(Execution.created_at, Execution.id)
                .limit(1)
            )
            if execution is None:
                db.commit()
                return None

            now = utcnow()
            execution.status = ExecutionStatus.RUNNING.value
            execution.started_at = execution.started_at or now
            execution.worker_id = self.worker_id
            execution.claimed_at = now
            worker.current_load += 1

            db.add(
                Event(
                    execution_id=execution.id,
                    type="worker.execution.claimed",
                    level="INFO",
                    message="Execution claimed by worker",
                    payload={
                        "worker_id": self.worker_id,
                        "stage": ExecutionStage.CREATED.value,
                    },
                    created_at=now,
                )
            )
            db.commit()
            return execution.id
        finally:
            db.close()

    def release_execution(self, execution_id: int) -> None:
        db = self.session_factory()
        try:
            worker = self._get_worker(db)
            execution = db.get(Execution, execution_id)
            if execution is None or execution.worker_id != self.worker_id:
                db.rollback()
                return

            worker.current_load = max(0, worker.current_load - 1)
            db.commit()
        finally:
            db.close()

    def _update_worker_heartbeat(self) -> Worker:
        db = self.session_factory()
        try:
            worker = self._get_worker(db)
            if worker.status != WorkerStatus.ONLINE.value:
                raise WorkerNotRegisteredError(
                    f"Worker {self.worker_id!r} is not online"
                )
            worker.heartbeat_at = utcnow()
            db.commit()
            db.refresh(worker)
            return worker
        finally:
            db.close()

    def _get_worker(self, db: Session) -> Worker:
        worker = db.scalar(
            select(Worker).where(Worker.worker_id == self.worker_id)
        )
        if worker is None:
            raise WorkerNotRegisteredError(
                f"Worker {self.worker_id!r} is not registered"
            )
        return worker
