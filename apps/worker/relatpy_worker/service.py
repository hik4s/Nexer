from datetime import datetime, timezone
import os
import socket

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.enums import (
    ExecutionAutomationStatus,
    ExecutionStage,
    ExecutionStatus,
    WorkerStatus,
)
from app.models import Event, Execution, ExecutionAutomation, Worker


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

    def recover_stale_executions(self, *, stale_after_seconds: int = 300) -> int:
        if stale_after_seconds < 1:
            raise ValueError("stale_after_seconds must be >= 1")

        db = self.session_factory()
        recovered = 0
        try:
            db.execute(text("BEGIN IMMEDIATE"))
            current_worker = self._get_worker(db)
            now = utcnow()
            cutoff = now.timestamp() - stale_after_seconds

            running = list(
                db.scalars(
                    select(Execution)
                    .where(
                        Execution.status == ExecutionStatus.RUNNING.value,
                        Execution.worker_id.is_not(None),
                        Execution.claimed_at.is_not(None),
                    )
                    .order_by(Execution.id)
                ).all()
            )

            for execution in running:
                assigned_worker = db.scalar(
                    select(Worker).where(
                        Worker.worker_id == execution.worker_id
                    )
                )
                if not self._should_recover_execution(
                    execution=execution,
                    assigned_worker=assigned_worker,
                    current_worker=current_worker,
                    cutoff=cutoff,
                ):
                    continue

                previous_worker_id = execution.worker_id
                self._mark_execution_lost(
                    db,
                    execution=execution,
                    now=now,
                    previous_worker_id=previous_worker_id,
                )

                if (
                    assigned_worker is not None
                    and assigned_worker.worker_id != self.worker_id
                ):
                    assigned_worker.current_load = max(
                        0, assigned_worker.current_load - 1
                    )
                    if not self._worker_process_is_alive(assigned_worker.pid):
                        assigned_worker.status = WorkerStatus.OFFLINE.value
                        assigned_worker.stopped_at = now
                        assigned_worker.current_load = 0

                recovered += 1

            db.commit()
            return recovered
        finally:
            db.close()

    def _should_recover_execution(
        self,
        *,
        execution: Execution,
        assigned_worker: Worker | None,
        current_worker: Worker,
        cutoff: float,
    ) -> bool:
        if execution.claimed_at is None:
            return False

        claimed_timestamp = execution.claimed_at.timestamp()
        if claimed_timestamp >= cutoff:
            return False

        if assigned_worker is None:
            return True

        if assigned_worker.worker_id == self.worker_id:
            return execution.claimed_at < current_worker.started_at

        if assigned_worker.status == WorkerStatus.OFFLINE.value:
            return True

        return assigned_worker.pid is not None and not self._worker_process_is_alive(
            assigned_worker.pid
        )

    @staticmethod
    def _worker_process_is_alive(pid: int) -> bool:
        if os.name == "nt":
            import ctypes

            PROCESS_SYNCHRONIZE = 0x00100000
            ERROR_INVALID_PARAMETER = 87

            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_SYNCHRONIZE,
                False,
                pid,
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True

            error = ctypes.GetLastError()
            return error != ERROR_INVALID_PARAMETER

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _mark_execution_lost(
        self,
        db: Session,
        *,
        execution: Execution,
        now: datetime,
        previous_worker_id: str | None,
    ) -> None:
        execution.status = ExecutionStatus.FAILED.value
        execution.finished_at = now
        execution.worker_id = None
        execution.claimed_at = None

        items = list(
            db.scalars(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution.id,
                    ~ExecutionAutomation.status.in_(
                        [
                            ExecutionAutomationStatus.SUCCEEDED.value,
                            ExecutionAutomationStatus.FAILED.value,
                            ExecutionAutomationStatus.CANCELLED.value,
                            ExecutionAutomationStatus.REMOVED.value,
                        ]
                    ),
                )
            ).all()
        )

        for item in items:
            item.status = ExecutionAutomationStatus.FAILED.value
            item.stage = ExecutionStage.FAILED.value
            item.finished_at = now
            item.last_progress_at = now
            item.error_type = "WORKER_LOST"
            item.error_detail = (
                "Execution interrupted because its worker was lost."
            )

        db.add(
            Event(
                execution_id=execution.id,
                type="worker.execution.recovered",
                level="ERROR",
                message="Execution recovered after worker loss",
                payload={
                    "previous_worker_id": previous_worker_id,
                    "status": ExecutionStatus.FAILED.value,
                    "reason": "WORKER_LOST",
                },
                created_at=now,
            )
        )

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
