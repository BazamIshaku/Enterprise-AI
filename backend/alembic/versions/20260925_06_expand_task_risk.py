"""Allow descriptive governed task risk levels."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_06"
down_revision = "20260925_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("work_tasks", "risk_level", existing_type=sa.String(length=16), type_=sa.String(length=24), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("work_tasks", "risk_level", existing_type=sa.String(length=24), type_=sa.String(length=16), existing_nullable=False)
