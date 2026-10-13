"""Create the initial Nexer persistence schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code", name="uq_automations_code"),
    )
    op.create_index("ix_automations_status", "automations", ["status"])

    op.create_table(
        "automation_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("automation_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("recipe", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=True),
        sa.Column("test_status", sa.String(length=20), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["automation_id"],
            ["automations.id"],
            name="fk_automation_versions_automation",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "automation_id",
            "version",
            name="uq_automation_version",
        ),
    )
    op.create_index(
        "ix_automation_versions_automation_id",
        "automation_versions",
        ["automation_id"],
    )

    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("path_reference", sa.String(length=1024), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_test_status", sa.String(length=20), nullable=True),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("code", name="uq_destinations_code"),
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("requested_by", sa.String(length=200), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("send_to_network", sa.Boolean(), nullable=False),
        sa.Column("keep_local_copy", sa.Boolean(), nullable=False),
        sa.Column("overwrite_existing", sa.Boolean(), nullable=False),
        sa.Column("test_mode", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_executions_status_created_at", "executions", ["status", "created_at"])

    op.create_table(
        "execution_automations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("automation_id", sa.Integer(), nullable=False),
        sa.Column("automation_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_progress_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["executions.id"],
            name="fk_execution_automations_execution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["automation_id"],
            ["automations.id"],
            name="fk_execution_automations_automation",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "execution_id",
            "automation_id",
            name="uq_execution_automation",
        ),
    )
    op.create_index(
        "ix_execution_automations_execution_id",
        "execution_automations",
        ["execution_id"],
    )
    op.create_index(
        "ix_execution_automations_automation_id",
        "execution_automations",
        ["automation_id"],
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("execution_automation_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["executions.id"],
            name="fk_events_execution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["execution_automation_id"],
            ["execution_automations.id"],
            name="fk_events_execution_automation",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_events_execution_id", "events", ["execution_id"])
    op.create_index(
        "ix_events_execution_automation_id",
        "events",
        ["execution_automation_id"],
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_automation_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("local_path", sa.String(length=2048), nullable=True),
        sa.Column("network_path", sa.String(length=2048), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_automation_id"],
            ["execution_automations.id"],
            name="fk_artifacts_execution_automation",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_artifacts_execution_automation_id",
        "artifacts",
        ["execution_automation_id"],
    )

    op.create_table(
        "checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_automation_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=100), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_automation_id"],
            ["execution_automations.id"],
            name="fk_checkpoints_execution_automation",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_checkpoints_execution_automation_step",
        "checkpoints",
        ["execution_automation_id", "step_index"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_checkpoints_execution_automation_step",
        table_name="checkpoints",
    )
    op.drop_table("checkpoints")

    op.drop_index("ix_artifacts_execution_automation_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_events_execution_automation_id", table_name="events")
    op.drop_index("ix_events_execution_id", table_name="events")
    op.drop_table("events")

    op.drop_index(
        "ix_execution_automations_automation_id",
        table_name="execution_automations",
    )
    op.drop_index(
        "ix_execution_automations_execution_id",
        table_name="execution_automations",
    )
    op.drop_table("execution_automations")

    op.drop_index("ix_executions_status_created_at", table_name="executions")
    op.drop_table("executions")

    op.drop_table("destinations")

    op.drop_index(
        "ix_automation_versions_automation_id",
        table_name="automation_versions",
    )
    op.drop_table("automation_versions")

    op.drop_index("ix_automations_status", table_name="automations")
    op.drop_table("automations")
