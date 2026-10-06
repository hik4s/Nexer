import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.enums import ExecutionStatus, WorkerStatus
from app.models import Automation, AutomationVersion, Execution, ExecutionAutomation, Worker
from relatpy_worker.service import WorkerService


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


class WorkerServiceTests(unittest.TestCase):
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
        db = self.session_factory()
        try:
            automation = Automation(
                code="worker-test",
                name="Worker Test",
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


if __name__ == "__main__":
    unittest.main()
