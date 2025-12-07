"""fix pipeline_runs sequence

Revision ID: e4f5g6h7i8j9
Revises: d3b4e5f6g7h8
Create Date: 2025-11-17 02:18:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4f5g6h7i8j9"
down_revision: Union[str, Sequence[str], None] = "d3b4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix the pipeline_runs ID sequence."""
    # Only run for PostgreSQL - SQLite uses AUTOINCREMENT and doesn't need this
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Reset the sequence to the maximum ID + 1
        # This fixes the duplicate key error when creating new pipeline runs
        op.execute("""
            SELECT setval('pipeline_runs_id_seq', COALESCE((SELECT MAX(id) FROM pipeline_runs), 0) + 1, false);
        """)


def downgrade() -> None:
    """Downgrade not needed for sequence reset."""
    pass
