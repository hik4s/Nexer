import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.enums import (
    ExecutionAutomationStatus,
    ExecutionStatus,
    WorkerStatus,
)
from app.models import (
    Automation,
    AutomationVersion,
    Event,
    Execution,
    ExecutionAutomation,
    Worker,
)
from relatpy_worker.service import WorkerService


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


class WorkerServiceTests(unittest.TestCase):
    _execution_seed = 0

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "relatpy-worker.db"

        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(config, "head")

        cls.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        cls.tmp.cleanup()

    def setUp(self):
        db = self.session_factory()
        try:
            for table in (
                "events",
                "execution_automations",
                "executions",
                "automation_versions",
                "automations",
                "workers",
            ):
                db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def _seed_queued_execution(self):
        type(self)._execution_seed += 1
        seed = type(self)._execution_seed
        db = self.session_factory()
        try:
            automation = Automation(
                code=f"worker-test-{seed}",
                name=f"Worker Test {seed}",
                status="PUBLISHED",
                current_version=1,
            )
            db.add(automation)
            db.flush()
            db.add(
                AutomationVersion(
                    automation_id=automation.id,
                    version=1,
                    recipe={"schema_version": 1, "name": "worker-test", "steps": []},
                    test_status="PASSED",
                    published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None),
                )
            )
            execution = Execution(
                name="Worker Execution",
                status=ExecutionStatus.QUEUED.value,
                send_to_network=False,
                keep_local_copy=True,
                overwrite_existing=False,
                test_mode=True,
                cancel_requested=False,
            )
            db.add(execution)
            db.flush()
            db.add(
                ExecutionAutomation(
                    execution_id=execution.id,
                    automation_id=automation.id,
                    automation_version=1,
                    status="PENDING",
                    stage="CREATED",
                    attempts=0,
                )
            )
            db.commit()
            return execution.id
        finally:
            db.close()

    def test_worker_registers_online_and_updates_heartbeat(self):
        service = WorkerService(
            session_factory=self.session_factory,
            worker_id="worker-a",
            concurrency_limit=2,
            hostname="test-host",
            pid=1234,
        )

        worker = service.register()
        self.assertEqual(worker.worker_id, "worker-a")
        self.assertEqual(worker.status, WorkerStatus.ONLINE.value)
        first_heartbeat = worker.heartbeat_at

        worker = service.heartbeat()
        self.assertEqual(worker.status, WorkerStatus.ONLINE.value)
        self.assertGreaterEqual(worker.heartbeat_at, first_heartbeat)

        service.stop()

        db = self.session_factory()
        try:
            stored = db.get(Worker, worker.id)
            self.assertEqual(stored.status, WorkerStatus.OFFLINE.value)
            self.assertIsNotNone(stored.stopped_at)
        finally:
            db.close()

    def test_only_one_worker_can_claim_the_same_execution(self):
        execution_id = self._seed_queued_execution()
        first = WorkerService(
            session_factory=self.session_factory,
            worker_id="worker-a",
            concurrency_limit=1,
            hostname="host-a",
            pid=1,
        )
        second = WorkerService(
            session_factory=self.session_factory,
            worker_id="worker-b",
            concurrency_limit=1,
            hostname="host-b",
            pid=2,
        )
        first.register()
        second.register()

        claimed_first = first.claim_next()
        claimed_second = second.claim_next()

        self.assertEqual(claimed_first, execution_id)
        self.assertIsNone(claimed_second)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            self.assertEqual(execution.status, ExecutionStatus.RUNNING.value)
            self.assertEqual(execution.worker_id, "worker-a")
        finally:
            db.close()

        first.stop()
        second.stop()

    def test_claim_respects_concurrency_limit(self):
        execution_a = self._seed_queued_execution()
        execution_b = self._seed_queued_execution()
        service = WorkerService(
            session_factory=self.session_factory,
            worker_id="worker-a",
            concurrency_limit=1,
            hostname="host-a",
            pid=1,
        )
        service.register()

        self.assertEqual(service.claim_next(), execution_a)
        self.assertIsNone(service.claim_next())

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_b)
            self.assertEqual(execution.status, ExecutionStatus.QUEUED.value)
        finally:
            db.close()

        service.stop()

    def test_recover_stale_execution_from_lost_worker(self):
        execution_id = self._seed_queued_execution()
        old_time = __import__("datetime").datetime(2020, 1, 1)

        db = self.session_factory()
        try:
            worker = Worker(
                worker_id="lost-worker",
                status=WorkerStatus.ONLINE.value,
                hostname="old-host",
                pid=10,
                concurrency_limit=1,
                current_load=1,
                heartbeat_at=old_time,
                started_at=old_time,
                stopped_at=None,
                created_at=old_time,
            )
            db.add(worker)
            db.flush()

            execution = db.get(Execution, execution_id)
            execution.status = ExecutionStatus.RUNNING.value
            execution.worker_id = "lost-worker"
            execution.claimed_at = old_time
            db.commit()
        finally:
            db.close()

        recovery = WorkerService(
            session_factory=self.session_factory,
            worker_id="recovery-worker",
            concurrency_limit=1,
            hostname="new-host",
            pid=20,
        )
        recovery.register()

        recovered = recovery.recover_stale_executions(stale_after_seconds=60)

        self.assertEqual(recovered, 1)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            item = db.scalar(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution_id
                )
            )
            event = db.scalar(
                select(Event).where(
                    Event.execution_id == execution_id,
                    Event.type == "worker.execution.recovered",
                )
            )
            self.assertEqual(execution.status, ExecutionStatus.FAILED.value)
            self.assertIsNone(execution.worker_id)
            self.assertIsNone(execution.claimed_at)
            self.assertEqual(item.status, ExecutionAutomationStatus.FAILED.value)
            self.assertEqual(item.error_type, "WORKER_LOST")
            self.assertIsNotNone(event)
        finally:
            db.close()

        recovery.stop()

    def test_does_not_recover_live_foreign_worker_from_stale_heartbeat(self):
        execution_id = self._seed_queued_execution()
        old_time = __import__("datetime").datetime(2020, 1, 1)

        db = self.session_factory()
        try:
            db.add(
                Worker(
                    worker_id="live-worker",
                    status=WorkerStatus.ONLINE.value,
                    hostname="host",
                    pid=__import__("os").getpid(),
                    concurrency_limit=1,
                    current_load=1,
                    heartbeat_at=old_time,
                    started_at=old_time,
                    stopped_at=None,
                    created_at=old_time,
                )
            )
            db.flush()
            execution = db.get(Execution, execution_id)
            execution.status = ExecutionStatus.RUNNING.value
            execution.worker_id = "live-worker"
            execution.claimed_at = old_time
            db.commit()
        finally:
            db.close()

        recovery = WorkerService(
            session_factory=self.session_factory,
            worker_id="recovery-worker",
            concurrency_limit=1,
            hostname="new-host",
            pid=20,
        )
        recovery.register()

        recovered = recovery.recover_stale_executions(stale_after_seconds=60)

        self.assertEqual(recovered, 0)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            self.assertEqual(execution.status, ExecutionStatus.RUNNING.value)
            self.assertEqual(execution.worker_id, "live-worker")
        finally:
            db.close()

        recovery.stop()

    def test_recover_previous_incarnation_of_same_worker(self):
        execution_id = self._seed_queued_execution()
        old_time = __import__("datetime").datetime(2020, 1, 1)

        db = self.session_factory()
        try:
            worker = Worker(
                worker_id="restarted-worker",
                status=WorkerStatus.ONLINE.value,
                hostname="host",
                pid=10,
                concurrency_limit=1,
                current_load=1,
                heartbeat_at=old_time,
                started_at=old_time,
                stopped_at=None,
                created_at=old_time,
            )
            db.add(worker)
            db.flush()

            execution = db.get(Execution, execution_id)
            execution.status = ExecutionStatus.RUNNING.value
            execution.worker_id = "restarted-worker"
            execution.claimed_at = old_time
            db.commit()
        finally:
            db.close()

        restarted = WorkerService(
            session_factory=self.session_factory,
            worker_id="restarted-worker",
            concurrency_limit=1,
            hostname="host",
            pid=99,
        )
        restarted.register()

        recovered = restarted.recover_stale_executions(stale_after_seconds=60)

        self.assertEqual(recovered, 1)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            self.assertEqual(execution.status, ExecutionStatus.FAILED.value)
            self.assertIsNone(execution.worker_id)
            self.assertIsNone(execution.claimed_at)
        finally:
            db.close()

        restarted.stop()


if __name__ == "__main__":
    unittest.main()
