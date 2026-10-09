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
    Checkpoint,
)
from nexer_worker.processor import WorkerExecutionProcessor
from runner import RunResult
from nexer_worker.service import WorkerService


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



class CorporateTestClient:
    def __init__(self):
        self.copies = []
        self.released = []
        self.revoked = False

    def resolve(self, execution_id, system):
        if self.revoked:
            raise RuntimeError("corporate-canary")
        values = {"username": "corporate-canary-user", "password": "corporate-canary-password"}
        self.copies.append(values)
        return values

    def release(self, execution_id):
        self.released.append(execution_id)


class CorporateTestPolicy:
    def __init__(self, authorize):
        self.authorize = authorize

    def check(self):
        self.authorize()


class CorporateTestPage:
    def __init__(self):
        self.url = ""
        self.submitted = False
        self.closed = False
        self.calls = []

    def goto(self, url, **kwargs):
        self.url = url
        self.calls.append(("goto", url))

    def locator(self, selector):
        page = self
        class Locator:
            def fill(self, value, **kwargs):
                page.calls.append(("fill", selector, value))
            def click(self, **kwargs):
                page.submitted = True
                page.url = "https://indicadoresenergisaess.scl.corp/sgind/#/home"
            def count(self):
                return 0 if page.submitted else 1
            def is_visible(self):
                return selector == "app-home-page" and page.submitted
            def get_attribute(self, name):
                return None
        return Locator()

    def close(self):
        self.closed = True

    def wait_for_timeout(self, value):
        pass

class WorkerExecutionProcessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db_path = Path(cls.tmp.name) / "nexer-processor.db"

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
                "checkpoints",
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

    def test_unvalidated_corporate_renewal_never_reaches_browser(self):
        execution_id = self._seed_execution()
        with self.session_factory() as db:
            version = db.scalar(select(AutomationVersion))
            version.recipe = {**version.recipe, "authentication": {
                "login_selectors": ["#login"], "renewal": {
                    "login_url": "https://evil.example/", "username_ref": "SGIND.username",
                    "password_ref": "SGIND.password", "username_selector": "#user",
                    "password_selector": "#pass", "submit_selector": "#submit", "success_selector": "#ok"}}}
            db.commit()
        worker = WorkerService(session_factory=self.session_factory, worker_id="blocked-auth", pid=999)
        worker.register()
        page_factory = Mock(return_value=FakePage())
        processor = WorkerExecutionProcessor(session_factory=self.session_factory,
            worker_service=worker, page_factory=page_factory, downloads_root=Path(self.tmp.name) / "downloads")
        self.assertEqual(processor.process_once().status, ExecutionStatus.FAILED.value)
        page_factory.assert_not_called()

    def test_browser_exception_does_not_persist_secret(self):
        execution_id = self._seed_execution()
        worker = WorkerService(session_factory=self.session_factory, worker_id="safe-errors", pid=999)
        worker.register()
        def fail(*args):
            raise RuntimeError("synthetic-sensitive-canary")
        processor = WorkerExecutionProcessor(session_factory=self.session_factory,
            worker_service=worker, page_factory=fail, downloads_root=Path(self.tmp.name) / "downloads")
        self.assertEqual(processor.process_once().status, ExecutionStatus.FAILED.value)
        with self.session_factory() as db:
            item = db.scalar(select(ExecutionAutomation).where(ExecutionAutomation.execution_id == execution_id))
            self.assertNotIn("synthetic-sensitive-canary", item.error_detail or "")
            events = list(db.scalars(select(Event).where(Event.execution_id == execution_id)))
            self.assertNotIn("synthetic-sensitive-canary", repr([e.payload for e in events]))

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

            checkpoints = list(
                db.scalars(
                    select(Checkpoint)
                    .where(Checkpoint.execution_automation_id == item.id)
                    .order_by(Checkpoint.step_index)
                ).all()
            )
            self.assertEqual(
                [(checkpoint.step_id, checkpoint.step_index, checkpoint.status) for checkpoint in checkpoints],
                [
                    ("open", 0, "SUCCEEDED"),
                    ("fill_start", 1, "SUCCEEDED"),
                    ("fill_company", 2, "SUCCEEDED"),
                ],
            )
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


    def test_processor_builds_auth_guard_without_persisting_session_state(self):
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
        session_store.save.assert_not_called()
        page.storage_state.assert_not_called()
        worker.stop()




    def _set_corporate_system(self):
        db = self.session_factory()
        try:
            automation = db.scalar(select(Automation))
            automation.system = "SGIND"
            version = db.scalar(select(AutomationVersion))
            recipe = dict(version.recipe)
            recipe["steps"] = [
                {"id": "open", "action": "navigate",
                 "url": "https://indicadoresenergisaess.scl.corp/sgind/#/report"},
                {"id": "company", "action": "fill", "selector": "#company", "value": "{{company}}"}
            ]
            version.recipe = recipe
            db.commit()
        finally:
            db.close()

    def test_corporate_system_without_validated_adapter_never_creates_browser(self):
        execution_id = self._seed_execution()
        self._set_corporate_system()
        worker = WorkerService(session_factory=self.session_factory, worker_id="corp-gate",
                               concurrency_limit=1, hostname="test", pid=1001)
        worker.register()
        opened = []
        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory, worker_service=worker,
            page_factory=lambda *args: opened.append(True) or FakePage(),
            downloads_root=Path(self.tmp.name) / "downloads")
        result = processor.process_once()
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(opened, [])
        worker.stop()

    def test_corporate_processor_logs_in_then_runs_recipe_and_releases_channel(self):
        import inspect
        from unittest.mock import patch
        self.assertIn("corporate_page_factory", inspect.signature(WorkerExecutionProcessor).parameters,
                      "Worker lacks a restricted corporate page factory")
        execution_id = self._seed_execution()
        self._set_corporate_system()
        worker = WorkerService(session_factory=self.session_factory, worker_id="corp-flow",
                               concurrency_limit=1, hostname="test", pid=1001)
        worker.register()
        page = CorporateTestPage()
        client = CorporateTestClient()
        def factory(system, authorize):
            self.assertEqual(system, "SGIND")
            page.corporate_policy = CorporateTestPolicy(authorize)
            return page
        def unrestricted(*args):
            self.fail("Corporate execution used the unrestricted browser")
        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory, worker_service=worker,
            page_factory=unrestricted, corporate_page_factory=factory,
            downloads_root=Path(self.tmp.name) / "downloads", credential_client=client)
        with patch("nexer_worker.processor.require_validated_adapter"):
            result = processor.process_once()
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertTrue(page.submitted)
        self.assertTrue(page.closed)
        self.assertEqual(client.released, [execution_id])
        self.assertTrue(all(values == {} for values in client.copies))
        self.assertIn(("fill", "#company", "001"), page.calls)
        db = self.session_factory()
        try:
            for event in db.scalars(select(Event)):
                self.assertNotIn("corporate-canary", str(event.payload))
        finally:
            db.close()
        worker.stop()

    def test_corporate_revocation_stops_next_action_and_closes_page(self):
        import inspect
        from unittest.mock import patch
        self.assertIn("corporate_page_factory", inspect.signature(WorkerExecutionProcessor).parameters)
        execution_id = self._seed_execution()
        self._set_corporate_system()
        worker = WorkerService(session_factory=self.session_factory, worker_id="corp-revoke",
                               concurrency_limit=1, hostname="test", pid=1001)
        worker.register()
        page = CorporateTestPage()
        client = CorporateTestClient()
        def factory(system, authorize):
            page.corporate_policy = CorporateTestPolicy(authorize)
            return page
        original_goto = page.goto
        def revoke_after_first_action(url, **kwargs):
            original_goto(url, **kwargs)
            if url.endswith("#/report"):
                client.revoked = True
        page.goto = revoke_after_first_action
        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory, worker_service=worker,
            page_factory=lambda *args: self.fail("Unrestricted factory used"),
            corporate_page_factory=factory, downloads_root=Path(self.tmp.name) / "downloads",
            credential_client=client)
        with patch("nexer_worker.processor.require_validated_adapter"):
            result = processor.process_once()
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(page.closed)
        self.assertNotIn(("fill", "#company", "001"), page.calls)
        self.assertEqual(client.released, [execution_id])
        worker.stop()

    def test_corporate_revocation_during_last_action_cannot_report_success(self):
        import inspect
        from unittest.mock import patch
        self.assertIn("corporate_page_factory", inspect.signature(WorkerExecutionProcessor).parameters)
        execution_id = self._seed_execution()
        self._set_corporate_system()
        db = self.session_factory()
        try:
            version = db.scalar(select(AutomationVersion))
            recipe = dict(version.recipe)
            recipe["steps"] = recipe["steps"][:1]
            version.recipe = recipe
            db.commit()
        finally:
            db.close()
        worker = WorkerService(session_factory=self.session_factory, worker_id="corp-revoke",
                               concurrency_limit=1, hostname="test", pid=1001)
        worker.register()
        page = CorporateTestPage()
        client = CorporateTestClient()
        def factory(system, authorize):
            page.corporate_policy = CorporateTestPolicy(authorize)
            return page
        original_goto = page.goto
        def revoke_after_first_action(url, **kwargs):
            original_goto(url, **kwargs)
            if url.endswith("#/report"):
                client.revoked = True
        page.goto = revoke_after_first_action
        processor = WorkerExecutionProcessor(
            session_factory=self.session_factory, worker_service=worker,
            page_factory=lambda *args: self.fail("Unrestricted factory used"),
            corporate_page_factory=factory, downloads_root=Path(self.tmp.name) / "downloads",
            credential_client=client)
        with patch("nexer_worker.processor.require_validated_adapter"):
            result = processor.process_once()
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(page.closed)
        self.assertNotIn(("fill", "#company", "001"), page.calls)
        self.assertEqual(client.released, [execution_id])
        worker.stop()

if __name__ == "__main__":
    unittest.main()
