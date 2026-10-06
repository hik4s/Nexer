from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.enums import (
    AutomationStatus,
    ExecutionAutomationStatus,
    ExecutionStage,
    ExecutionStatus,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Automation(Base):
    __tablename__ = "automations"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default=AutomationStatus.DRAFT.value, nullable=False)
    current_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    versions: Mapped[list["AutomationVersion"]] = relationship(
        back_populates="automation",
        cascade="all, delete-orphan",
    )


class AutomationVersion(Base):
    __tablename__ = "automation_versions"
    __table_args__ = (
        UniqueConstraint("automation_id", "version", name="uq_automation_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    automation_id: Mapped[int] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(200))
    test_status: Mapped[str | None] = mapped_column(String(20))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    automation: Mapped[Automation] = relationship(back_populates="versions")


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_test_status: Mapped[str | None] = mapped_column(String(20))
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime)


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(200))
    period_start: Mapped[datetime | None] = mapped_column(DateTime)
    period_end: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.QUEUED.value, nullable=False)
    send_to_network: Mapped[bool] = mapped_column(default=False, nullable=False)
    keep_local_copy: Mapped[bool] = mapped_column(default=True, nullable=False)
    overwrite_existing: Mapped[bool] = mapped_column(default=False, nullable=False)
    test_mode: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)


class ExecutionAutomation(Base):
    __tablename__ = "execution_automations"
    __table_args__ = (
        UniqueConstraint("execution_id", "automation_id", name="uq_execution_automation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    automation_id: Mapped[int] = mapped_column(
        ForeignKey("automations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    automation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ExecutionAutomationStatus.PENDING.value,
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(
        String(30),
        default=ExecutionStage.CREATED.value,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_progress_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_automation_id: Mapped[int | None] = mapped_column(
        ForeignKey("execution_automations.id", ondelete="CASCADE"),
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_automation_id: Mapped[int] = mapped_column(
        ForeignKey("execution_automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(2048))
    network_path: Mapped[str | None] = mapped_column(String(2048))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    size: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_automation_id: Mapped[int] = mapped_column(
        ForeignKey("execution_automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[str] = mapped_column(String(100), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
