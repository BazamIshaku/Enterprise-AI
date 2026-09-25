"""Add governed AI employee work tasks and communication."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_05"
down_revision = "20260925_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assistant_id", sa.String(36), sa.ForeignKey("assistants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supervisor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(100), nullable=False, server_default="Waiting for the AI employee"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="standard"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("workspace_id", "assistant_id", "created_by", "supervisor_id"):
        op.create_index(f"ix_work_tasks_{column}", "work_tasks", [column])
    op.create_table(
        "task_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_type", sa.String(16), nullable=False),
        sa.Column("author_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("author_name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default="message"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_messages_task_id", "task_messages", ["task_id"])
    op.create_index("ix_task_messages_workspace_id", "task_messages", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("task_messages")
    op.drop_table("work_tasks")
