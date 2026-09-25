"""Add persisted knowledge-processing progress and indexed chunks."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_04"
down_revision = "20260925_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_documents", sa.Column("stage", sa.String(length=80), nullable=False, server_default="Waiting securely in the training queue"))
    op.add_column("knowledge_documents", sa.Column("progress", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("knowledge_documents", sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("knowledge_documents", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assistant_id", sa.String(length=36), sa.ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "sequence", name="uq_knowledge_chunk_document_sequence"),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_assistant_id", "knowledge_chunks", ["assistant_id"])
    op.create_index("ix_knowledge_chunks_workspace_id", "knowledge_chunks", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_column("knowledge_documents", "processed_at")
    op.drop_column("knowledge_documents", "chunk_count")
    op.drop_column("knowledge_documents", "progress")
    op.drop_column("knowledge_documents", "stage")
