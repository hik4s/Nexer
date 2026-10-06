"""Add worker registry and execution claim metadata."""

from alembic import op
import sqlalchemy as sa


revision = "0002_worker_registry"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column("worker_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_executions_worker_id",
        "executions",
        ["worker_id"],
    )

    op.create_table(
        "workers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("concurrency_limit", sa.Integer(), nullable=False),
        sa.Column("current_load", sa.Integer(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("worker_id", name="uq_workers_worker_id"),
    )
    op.create_index(
        "ix_workers_status_heartbeat_at",
        "workers",
        ["status", "heartbeat_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workers_status_heartbeat_at", table_name="workers")
    op.drop_table("workers")
    op.drop_index("ix_executions_worker_id", table_name="executions")
    op.drop_column("executions", "claimed_at")
    op.drop_column("executions", "worker_id")
