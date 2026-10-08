from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select

from app.enums import ExecutionAutomationStatus, ExecutionStage, ExecutionStatus
from app.models import AutomationVersion, Checkpoint, Event, Execution, ExecutionAutomation
from auth_guard import build_auth_guard
from credentials import KeyringCredentialProvider
from context import ExecutionContext
from runner import RecipeRunner
from session_store import SessionStateStore


@dataclass(frozen=True)
class ProcessResult:
    execution_id: int | None
    status: str


class WorkerExecutionProcessor:
    def __init__(
        self,
        *,
        session_factory,
        worker_service,
        page_factory: Callable,
        downloads_root: Path,
        runner=None,
        secret_provider=None,
        session_state_store=None,
    ):
        if page_factory is None:
            raise ValueError("page_factory is required")

        self.session_factory = session_factory
        self.worker_service = worker_service
        self.page_factory = page_factory
        self.downloads_root = Path(downloads_root)
        self.runner = runner or RecipeRunner()
        self.secret_provider = secret_provider or KeyringCredentialProvider()
        self.session_state_store = session_state_store or SessionStateStore()

    def process_once(self) -> ProcessResult:
        execution_id = self.worker_service.claim_next()
        if execution_id is None:
            return ProcessResult(execution_id=None, status="IDLE")

        try:
            return self._process_execution(execution_id)
        finally:
            self.worker_service.release_execution(execution_id)

    def _process_execution(self, execution_id: int) -> ProcessResult:
        execution, items = self._load_execution(execution_id)

        for item in items:
            if execution.cancel_requested:
                self._cancel_item(execution_id, item.id)
                continue

            self._run_item(execution, item)

        return self._finish_execution(execution_id)

    def _load_execution(self, execution_id: int):
        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            if execution is None:
                raise RuntimeError("EXECUTION_NOT_FOUND")

            items = list(
                db.scalars(
                    select(ExecutionAutomation)
                    .where(ExecutionAutomation.execution_id == execution_id)
                    .order_by(ExecutionAutomation.id)
                ).all()
            )
            return execution, items
        finally:
            db.close()

    def _run_item(self, execution: Execution, item: ExecutionAutomation) -> None:
        try:
            recipe = self._load_recipe(item.automation_id, item.automation_version)
        except Exception as exc:
            self._mark_failed(
                execution.id,
                item.id,
                error_type=type(exc).__name__,
                error_detail=str(exc),
            )
            return

        self._update_item(
            item.id,
            status=ExecutionAutomationStatus.RUNNING.value,
            stage=ExecutionStage.CREATED.value,
            attempts=item.attempts + 1,
            started_at=self._now(),
            last_progress_at=self._now(),
        )
        self._emit(
            execution.id,
            item.id,
            "automation.started",
            {
                "automation_id": item.automation_id,
                "automation_version": item.automation_version,
                "stage": ExecutionStage.CREATED.value,
            },
        )

        page = None
        try:
            page = self.page_factory(execution, item, recipe)
            variables = self._execution_variables(execution)
            downloads_dir = (
                self.downloads_root
                / str(execution.id)
                / str(item.id)
            )
            context = ExecutionContext(
                page=page,
                variables=variables,
                downloads_dir=downloads_dir,
                dry_run=False,
                emit=lambda event: self._emit_runtime_event(
                    execution.id,
                    item.id,
                    event,
                ),
                secret_provider=self.secret_provider,
                cancellation_requested=lambda: self._execution_cancel_requested(
                    execution.id
                ),
                auth_guard=build_auth_guard(
                    recipe.get("authentication"),
                    credential_provider=self.secret_provider,
                ),
            )
            result = self.runner.run(recipe, context)
            now = self._now()

            if result.cancelled:
                self._cancel_item(execution.id, item.id)
            elif result.failed_step_id is None:
                self._persist_session_state(recipe, page)
                self._update_item(
                    item.id,
                    status=ExecutionAutomationStatus.SUCCEEDED.value,
                    stage=ExecutionStage.FINISHED.value,
                    finished_at=now,
                    last_progress_at=now,
                    error_type=None,
                    error_detail=None,
                )
                self._emit(
                    execution.id,
                    item.id,
                    "automation.finished",
                    {
                        "status": ExecutionAutomationStatus.SUCCEEDED.value,
                        "stage": ExecutionStage.FINISHED.value,
                        "completed_steps": result.completed_steps,
                    },
                )
            else:
                self._mark_failed(
                    execution.id,
                    item.id,
                    error_type="RUNTIME_ERROR",
                    error_detail=result.error,
                )
        except Exception as exc:
            self._mark_failed(
                execution.id,
                item.id,
                error_type=type(exc).__name__,
                error_detail=str(exc),
            )
        finally:
            close = getattr(page, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    self._emit(
                        execution.id,
                        item.id,
                        "browser.close_failed",
                        {"error_type": type(exc).__name__},
                        level="WARNING",
                    )


    def _persist_session_state(self, recipe: dict, page) -> None:
        authentication = recipe.get("authentication") or {}
        reference = authentication.get("session_ref")
        if not reference:
            return

        storage_state = getattr(page, "storage_state", None)
        if not callable(storage_state):
            raise RuntimeError("SESSION_STATE_UNAVAILABLE")

        self.session_state_store.save(reference, storage_state())

    def _execution_cancel_requested(self, execution_id: int) -> bool:
        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            return bool(execution and execution.cancel_requested)
        finally:
            db.close()

    def _load_recipe(self, automation_id: int, version: int) -> dict:
        db = self.session_factory()
        try:
            record = db.scalar(
                select(AutomationVersion).where(
                    AutomationVersion.automation_id == automation_id,
                    AutomationVersion.version == version,
                )
            )
            if record is None:
                raise RuntimeError("AUTOMATION_VERSION_NOT_FOUND")
            return dict(record.recipe)
        finally:
            db.close()

    @staticmethod
    def _execution_variables(execution: Execution) -> dict:
        variables = dict(execution.inputs or {})
        if execution.period_start is not None:
            variables["period_start"] = execution.period_start.date().isoformat()
        if execution.period_end is not None:
            variables["period_end"] = execution.period_end.date().isoformat()
        return variables

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _mark_failed(
        self,
        execution_id: int,
        item_id: int,
        *,
        error_type: str,
        error_detail: str | None,
    ) -> None:
        now = self._now()
        detail = (error_detail or "").strip()[:4000] or None
        self._update_item(
            item_id,
            status=ExecutionAutomationStatus.FAILED.value,
            stage=ExecutionStage.FAILED.value,
            finished_at=now,
            last_progress_at=now,
            error_type=error_type[:100],
            error_detail=detail,
        )
        self._emit(
            execution_id,
            item_id,
            "automation.failed",
            {
                "status": ExecutionAutomationStatus.FAILED.value,
                "stage": ExecutionStage.FAILED.value,
                "error_type": error_type[:100],
            },
            level="ERROR",
        )

    def _cancel_item(self, execution_id: int, item_id: int) -> None:
        now = self._now()
        self._update_item(
            item_id,
            status=ExecutionAutomationStatus.CANCELLED.value,
            stage=ExecutionStage.CANCELLED.value,
            finished_at=now,
            last_progress_at=now,
        )
        self._emit(
            execution_id,
            item_id,
            "automation.cancelled",
            {"status": ExecutionAutomationStatus.CANCELLED.value},
        )

    def _finish_execution(self, execution_id: int) -> ProcessResult:
        db = self.session_factory()
        try:
            execution = db.get(Execution, execution_id)
            if execution is None:
                raise RuntimeError("EXECUTION_NOT_FOUND")

            items = list(
                db.scalars(
                    select(ExecutionAutomation).where(
                        ExecutionAutomation.execution_id == execution_id
                    )
                ).all()
            )
            statuses = {item.status for item in items}

            if execution.cancel_requested and (
                statuses - {
                    ExecutionAutomationStatus.SUCCEEDED.value,
                    ExecutionAutomationStatus.FAILED.value,
                    ExecutionAutomationStatus.CANCELLED.value,
                }
                == set()
            ):
                status = ExecutionStatus.CANCELLED.value
            elif statuses == {ExecutionAutomationStatus.SUCCEEDED.value}:
                status = ExecutionStatus.SUCCEEDED.value
            elif (
                ExecutionAutomationStatus.SUCCEEDED.value in statuses
                and ExecutionAutomationStatus.FAILED.value in statuses
            ):
                status = ExecutionStatus.PARTIAL.value
            else:
                status = ExecutionStatus.FAILED.value

            now = self._now()
            execution.status = status
            execution.finished_at = now
            db.commit()
        finally:
            db.close()

        self._emit(
            execution_id,
            None,
            "execution.finished",
            {"status": status},
        )
        return ProcessResult(execution_id=execution_id, status=status)

    def _update_item(self, item_id: int, **changes) -> None:
        db = self.session_factory()
        try:
            item = db.get(ExecutionAutomation, item_id)
            if item is None:
                return
            for key, value in changes.items():
                setattr(item, key, value)
            db.commit()
        finally:
            db.close()

    def _emit_runtime_event(self, execution_id: int, item_id: int, event: dict) -> None:
        event_type = str(event.get("type", "runtime.event"))
        payload = {key: value for key, value in event.items() if key != "type"}

        if event_type == "checkpoint":
            self._persist_checkpoint(
                item_id,
                step_id=event.get("step_id"),
                step_index=event.get("step_index"),
                status=event.get("status"),
            )

        self._emit(
            execution_id,
            item_id,
            event_type,
            payload,
            update_progress=True,
        )

    def _persist_checkpoint(
        self,
        item_id: int,
        *,
        step_id,
        step_index,
        status,
    ) -> None:
        if (
            not isinstance(step_id, str)
            or type(step_index) is not int
            or not isinstance(status, str)
        ):
            return

        db = self.session_factory()
        try:
            db.add(
                Checkpoint(
                    execution_automation_id=item_id,
                    step_id=step_id,
                    step_index=step_index,
                    status=status,
                    created_at=self._now(),
                )
            )
            db.commit()
        finally:
            db.close()

    def _emit(
        self,
        execution_id: int,
        item_id: int | None,
        event_type: str,
        payload: dict,
        *,
        level: str = "INFO",
        update_progress: bool = False,
    ) -> None:
        now = self._now()
        db = self.session_factory()
        try:
            if update_progress and item_id is not None:
                item = db.get(ExecutionAutomation, item_id)
                if item is not None:
                    item.last_progress_at = now

            db.add(
                Event(
                    execution_id=execution_id,
                    execution_automation_id=item_id,
                    type=event_type,
                    level=level,
                    message=_message_for(event_type),
                    payload=payload or None,
                    created_at=now,
                )
            )
            db.commit()
        finally:
            db.close()


def _message_for(event_type: str) -> str:
    return event_type.replace(".", " ")
