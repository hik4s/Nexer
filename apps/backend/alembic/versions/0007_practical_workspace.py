"""Access groups and favorite routines; no credential persistence."""
from alembic import op
import sqlalchemy as sa
revision = "0007_practical_workspace"
down_revision = "0006_execution_batches"
branch_labels = depends_on = None
def upgrade():
    op.create_table("access_groups", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("routines", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("items", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    with op.batch_alter_table("login_profiles") as batch:
        batch.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_profile_access_group", "access_groups", ["group_id"], ["id"])
def downgrade():
    with op.batch_alter_table("login_profiles") as batch:
        batch.drop_constraint("fk_profile_access_group", type_="foreignkey"); batch.drop_column("group_id")
    op.drop_table("routines"); op.drop_table("access_groups")
