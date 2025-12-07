"""migrate old status values

Revision ID: d3b4e5f6g7h8
Revises: c2a3cb9f639e
Create Date: 2025-11-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3b4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "c2a3cb9f639e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - migrate old status values to new enum values."""
    # Update 'success' to 'completed'
    op.execute("UPDATE pipeline_runs SET status = 'completed' WHERE status = 'success'")
    # Update 'error' to 'failed'
    op.execute("UPDATE pipeline_runs SET status = 'failed' WHERE status = 'error'")


def downgrade() -> None:
    """Downgrade schema - revert to old status values."""
    # Revert 'completed' to 'success'
    op.execute("UPDATE pipeline_runs SET status = 'success' WHERE status = 'completed'")
    # Revert 'failed' to 'error'
    op.execute("UPDATE pipeline_runs SET status = 'error' WHERE status = 'failed'")
