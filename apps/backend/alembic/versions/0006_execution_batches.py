"""Group independent executions with transactional idempotency."""
from alembic import op
import sqlalchemy as sa
revision = "0006_execution_batches"
down_revision = "0005_execution_login_profiles"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("execution_batches", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("owner_key", sa.String(64), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("owner_key", "idempotency_key", name="uq_batch_idempotency"))
    with op.batch_alter_table("executions") as batch:
        batch.add_column(sa.Column("batch_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_execution_batch", "execution_batches", ["batch_id"], ["id"])
        batch.create_index("ix_executions_batch_id", ["batch_id"])

def downgrade():
    with op.batch_alter_table("executions") as batch:
        batch.drop_index("ix_executions_batch_id")
        batch.drop_constraint("fk_execution_batch", type_="foreignkey")
        batch.drop_column("batch_id")
    op.drop_table("execution_batches")
