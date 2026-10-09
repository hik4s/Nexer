"""Add declarative input variables to executions."""

from alembic import op
import sqlalchemy as sa


revision = "0003_execution_inputs"
down_revision = "0002_worker_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column(
            "inputs",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("executions", "inputs")
