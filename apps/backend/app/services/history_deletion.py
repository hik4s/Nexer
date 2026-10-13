"""Remove only completed execution records; generated files stay untouched."""
from sqlalchemy import delete, select
from app.models import Artifact, Checkpoint, Event, Execution, ExecutionAutomation

TERMINAL_STATUSES = frozenset({"SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"})


def delete_finished_executions(db, executions: list[Execution]) -> None:
    """Called within an existing transaction after checking all statuses."""
    if any(execution.status not in TERMINAL_STATUSES for execution in executions):
        raise ValueError("EXECUTION_NOT_TERMINAL")
    execution_ids = [execution.id for execution in executions]
    if not execution_ids:
        return
    item_ids = list(db.scalars(
        select(ExecutionAutomation.id).where(ExecutionAutomation.execution_id.in_(execution_ids))
    ))
    if item_ids:
        db.execute(delete(Artifact).where(Artifact.execution_automation_id.in_(item_ids)))
        db.execute(delete(Checkpoint).where(Checkpoint.execution_automation_id.in_(item_ids)))
    db.execute(delete(Event).where(Event.execution_id.in_(execution_ids)))
    db.execute(delete(ExecutionAutomation).where(ExecutionAutomation.execution_id.in_(execution_ids)))
    db.execute(delete(Execution).where(Execution.id.in_(execution_ids)))
