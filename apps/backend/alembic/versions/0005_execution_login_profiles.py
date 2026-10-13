"""Pin profile configuration to each execution; no credentials."""
from alembic import op
import sqlalchemy as sa
revision = "0005_execution_login_profiles"
down_revision = "0004_login_profiles"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("executions", sa.Column("login_profiles", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

def downgrade():
    op.drop_column("executions", "login_profiles")
