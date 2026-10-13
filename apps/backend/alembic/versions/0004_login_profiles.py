"""Reusable login configuration, never credentials."""
from alembic import op
import sqlalchemy as sa
revision = "0004_login_profiles"
down_revision = "0003_execution_inputs"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("login_profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("current_version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("login_profile_versions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("profile_id", sa.Integer(), sa.ForeignKey("login_profiles.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("configuration", sa.JSON(), nullable=False), sa.Column("published_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("profile_id", "version", name="uq_login_profile_version"))
    op.create_index("ix_login_profile_versions_profile_id", "login_profile_versions", ["profile_id"])

def downgrade():
    op.drop_table("login_profile_versions")
    op.drop_table("login_profiles")
