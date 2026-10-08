import tempfile
import unittest
from unittest.mock import Mock
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.enums import ExecutionAutomationStatus, ExecutionStage, ExecutionStatus
from app.models import (
    Automation,
    AutomationVersion,
    Event,
    Execution,
    ExecutionAutomation,
)
from relatpy_worker.processor import WorkerExecutionProcessor
from runner import RunResult
from relatpy_worker.service import WorkerService


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


class FakeLocator:
    def __init__(self, calls):
        self.calls = calls

    def fill(self, value, **kwargs):
        self.calls.append(("fill", value))


class FakePage:
    def __init__(self):
        self.calls = []
        self.current_url = None

    def goto(self, url, wait_until="domcontentloaded", timeout=30000):
        self.current_url = url
        self.calls.append(("goto", url, wait_until, timeout))

    def locator(self, selector):
        return FakeLocator(self.calls)


class WorkerExecutionProcessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "relatpy-processor.db"

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
                db.execute(text(f"DELETE FROM {table}"))
            db.commit()
        finally:
            db.close()

    def _seed_execution(self, *, failing=False):
        db = self.session_factory()
        try:
            automation = Automation(
                code="processor-test",
                name="Processor Test",
                status="PUBLISHED",
                current_version=1,
            )
            db.add(automation)
            db.flush()

            if failing:
                steps = [
                    {
                        "id": "unsupported_runtime",
                        "action": "click",
                        "selector": "#missing",
                    }
                ]
            else:
                steps = [
                    {
                        "id": "open",
                        "action": "navigate",
                        "url": "https://example.test/report",
                    },
                    {
                        "id": "fill_start",
                        "action": "fill",
                        "selector": "#start",
                        "value": "{{period_start}}",
                    },
                    {
                        "id": "fill_company",
                        "action": "fill",
                        "selector": "#company",
                        "value": "{{company}}",
                    },
                ]

            db.add(
                AutomationVersion(
                    automation_id=automation.id,
                    version=1,
                    recipe={
                        "schema_version": 1,
                        "name": "processor-test",
                        "variables": {
                            "period_start": {
                                "type": "string",
                                "required": True,
                            },
                            "company": {
                                "type": "string",
                                "required": True,
                            },
                        },
                        "steps": steps,
                        "output": {"type": "file"},
                    },
                    test_status="PASSED",
                    published_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )

            execution = Execution(
                name="Processor Execution",
                period_start=datetime(2026, 10, 1),
                period_end=datetime(2026, 10, 31),
                status=ExecutionStatus.QUEUED.value,
                send_to_network=False,
                keep_local_copy=True,
                overwrite_existing=False,
                test_mode=True,
                inputs={"company": "001"},
                cancel_requested=False,
            )
            db.add(execution)
            db.flush()
            db.add(
                ExecutionAutomation(
                    execution_id=execution.id,
                    automation_id=automation.id,
                    automation_version=1,
                    status=ExecutionAutomationStatus.PENDING.value,
                    stage=ExecutionStage.CREATED.value,
                    attempts=0,
                )
            )
            db.commit()
            return execution.id
        finally:
            db.close()

    def test_processor_runs_recipe_and_finishes_execution(self):
        execution_id = self._seed_execution()
        pages = []

        def page_factory(_execution, _item, _recipe):
            page = FakePage()
            pages.append(page)
            return page

        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="processor-worker",
            concurrency_limit=1,
            hostname="test-host",
            pid=999,
        )
        worker.register()

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=page_factory,
            downloads_root=Path(self.tmp.name) / "downloads",
        )

        result = processor.process_once()

        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED.value)
        self.assertEqual(pages[0].calls[0][0], "goto")
        self.assertIn(("fill", "2026-10-01"), pages[0].calls)
        self.assertIn(("fill", "001"), pages[0].calls)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            item = db.scalar(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution_id
                )
            )
            event_types = [
                event.type
                for event in db.scalars(
                    select(Event)
                    .where(Event.execution_id == execution_id)
                    .order_by(Event.id)
                ).all()
            ]
            self.assertEqual(execution.status, ExecutionStatus.SUCCEEDED.value)
            self.assertEqual(item.status, ExecutionAutomationStatus.SUCCEEDED.value)
            self.assertEqual(item.stage, ExecutionStage.FINISHED.value)
            self.assertIn("worker.execution.claimed", event_types)
            self.assertIn("automation.finished", event_types)
        finally:
            db.close()


    def test_processor_marks_execution_cancelled_when_runtime_stops(self):
        execution_id = self._seed_execution()
        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="cancel-worker",
            concurrency_limit=1,
            hostname="test-host",
            pid=1000,
        )
        worker.register()

        runner = Mock()
        def cancelled_run(_recipe, context):
            self.assertTrue(context.is_cancellation_requested())
            return RunResult(
                completed_steps=1,
                failed_step_id=None,
                cancelled=True,
            )

        runner.run.side_effect = cancelled_run

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=lambda _execution, _item, _recipe: FakePage(),
            downloads_root=Path(self.tmp.name) / "downloads",
            runner=runner,
        )

        def cancellation_after_claim(_execution_id):
            db = self.session_factory()
            try:
                execution = db.get(Execution, execution_id)
                execution.cancel_requested = True
                db.commit()
            finally:
                db.close()
            return True

        processor._execution_cancel_requested = cancellation_after_claim

        result = processor.process_once()

        self.assertEqual(result.status, ExecutionStatus.CANCELLED.value)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            item = db.scalar(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution_id
                )
            )
            self.assertEqual(execution.status, ExecutionStatus.CANCELLED.value)
            self.assertEqual(item.status, ExecutionAutomationStatus.CANCELLED.value)
        finally:
            db.close()

    def test_processor_marks_failed_automation_and_execution(self):
        execution_id = self._seed_execution(failing=True)

        def page_factory(_execution, _item, _recipe):
            return FakePage()

        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="processor-worker",
            concurrency_limit=1,
            hostname="test-host",
            pid=999,
        )
        worker.register()

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=page_factory,
            downloads_root=Path(self.tmp.name) / "downloads",
        )

        result = processor.process_once()

        self.assertEqual(result.execution_id, execution_id)
        self.assertEqual(result.status, ExecutionStatus.FAILED.value)

        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            item = db.scalar(
                select(ExecutionAutomation).where(
                    ExecutionAutomation.execution_id == execution_id
                )
            )
            self.assertEqual(execution.status, ExecutionStatus.FAILED.value)
            self.assertEqual(item.status, ExecutionAutomationStatus.FAILED.value)
            self.assertEqual(item.stage, ExecutionStage.FAILED.value)
            self.assertIsNotNone(item.error_type)
        finally:
            db.close()


    def test_processor_builds_auth_guard_and_persists_session_state(self):
        execution_id = self._seed_execution()
        db = self.session_factory()
        try:
            version = db.scalar(select(AutomationVersion))
            version.recipe = {
                **version.recipe,
                "authentication": {
                    "session_ref": "portal-a",
                    "login_selectors": ["#login"],
                },
            }
            db.commit()
        finally:
            db.close()

        page = Mock()
        page.storage_state.return_value = {"cookies": [], "origins": []}

        worker = WorkerService(
            session_factory=self.session_factory,
            worker_id="auth-worker",
            concurrency_limit=1,
            hostname="test-host",
            pid=1001,
        )
        worker.register()

        session_store = Mock()
        runner = Mock()
        runner.run.return_value = RunResult(
            completed_steps=1,
            failed_step_id=None,
            error=None,
            cancelled=False,
        )

        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory,
            worker_service=worker,
            page_factory=lambda *_args: page,
            downloads_root=Path(self.tmp.name) / "downloads",
            runner=runner,
            session_state_store=session_store,
        )

        result = processor.process_once()

        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED.value)
        context = runner.run.call_args.args[1]
        self.assertIsNotNone(context.auth_guard)
        session_store.save.assert_called_once_with(
            "portal-a",
            {"cookies": [], "origins": []},
        )
        worker.stop()



if __name__ == "__main__":
    unittest.main()
