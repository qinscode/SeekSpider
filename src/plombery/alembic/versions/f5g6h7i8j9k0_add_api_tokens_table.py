"""add api_tokens table

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2025-11-17 11:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5g6h7i8j9k0"
down_revision: Union[str, Sequence[str], None] = "e4f5g6h7i8j9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_tokens table."""
    op.create_table(
        'api_tokens',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    """Drop api_tokens table."""
    op.drop_table('api_tokens')
