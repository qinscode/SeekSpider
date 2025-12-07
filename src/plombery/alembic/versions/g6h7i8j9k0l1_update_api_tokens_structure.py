"""update api_tokens structure

Revision ID: g6h7i8j9k0l1
Revises: f5g6h7i8j9k0
Create Date: 2025-11-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g6h7i8j9k0l1"
down_revision: Union[str, Sequence[str], None] = "f5g6h7i8j9k0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update api_tokens table structure for authentication tokens."""
    # Drop the old table
    op.drop_table('api_tokens')

    # Create new table with correct structure
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_api_tokens_id'), 'api_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_api_tokens_token'), 'api_tokens', ['token'], unique=True)


def downgrade() -> None:
    """Revert to old api_tokens structure."""
    # Drop new table
    op.drop_index(op.f('ix_api_tokens_token'), table_name='api_tokens')
    op.drop_index(op.f('ix_api_tokens_id'), table_name='api_tokens')
    op.drop_table('api_tokens')

    # Recreate old table
    op.create_table(
        'api_tokens',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )
