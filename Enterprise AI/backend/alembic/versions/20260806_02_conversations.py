"""Add NIA conversations and messages."""
from alembic import op
import sqlalchemy as sa

revision = "20260806_02"
down_revision = "20260806_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("conversations", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_table("messages", sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("conversation_id", sa.String(length=36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(length=16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
