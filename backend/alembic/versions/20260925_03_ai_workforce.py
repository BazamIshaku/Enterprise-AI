"""Add governed AI employee templates and private knowledge records."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_03"
down_revision = "20260806_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistants", sa.Column("role_template_id", sa.String(length=80), nullable=False, server_default="legacy"))
    op.add_column("assistants", sa.Column("access_level", sa.String(length=32), nullable=False, server_default="admins_only"))
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assistant_id", sa.String(length=36), sa.ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_documents_workspace_id", "knowledge_documents", ["workspace_id"])
    op.create_index("ix_knowledge_documents_assistant_id", "knowledge_documents", ["assistant_id"])
    op.create_index("ix_knowledge_documents_uploaded_by", "knowledge_documents", ["uploaded_by"])


def downgrade() -> None:
    op.drop_table("knowledge_documents")
    op.drop_column("assistants", "access_level")
    op.drop_column("assistants", "role_template_id")
