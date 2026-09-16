"""Initial tenant-aware workspace schema."""
from alembic import op
import sqlalchemy as sa

revision = "20260806_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("email", sa.String(length=255), nullable=False), sa.Column("full_name", sa.String(length=120), nullable=False), sa.Column("password_hash", sa.String(length=255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("workspaces", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("slug", sa.String(length=80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)
    op.create_table("memberships", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(length=32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("user_id", "workspace_id", name="uq_membership_user_workspace"))
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_workspace_id", "memberships", ["workspace_id"])
    op.create_table("assistants", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("role", sa.String(length=160), nullable=False), sa.Column("department", sa.String(length=120), nullable=False), sa.Column("status", sa.String(length=16), nullable=False), sa.Column("capabilities", sa.JSON(), nullable=False), sa.Column("instructions", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_assistants_workspace_id", "assistants", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("assistants")
    op.drop_table("memberships")
    op.drop_table("workspaces")
    op.drop_table("users")
