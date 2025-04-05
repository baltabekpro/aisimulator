"""Add is_read column to messages table

Revision ID: add_is_read_column
Revises: dec32fa40317
Create Date: 2025-04-05 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_is_read_column'
down_revision: Union[str, None] = 'dec32fa40317'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Check database type
    conn = op.get_bind()
    is_sqlite = 'sqlite' in conn.engine.name.lower()
    
    # Add is_read column - use different approach for SQLite vs PostgreSQL
    try:
        if is_sqlite:
            # SQLite doesn't support ALTER TABLE ADD COLUMN with a NOT NULL constraint
            # without a default value, so we add with a default
            op.add_column('messages', sa.Column('is_read', sa.Boolean(), 
                                               nullable=False, server_default='0'))
        else:
            # PostgreSQL can handle this normally
            op.add_column('messages', sa.Column('is_read', sa.Boolean(), 
                                               nullable=False, server_default='false'))
    except Exception as e:
        # If column already exists or other error, log but continue
        print(f"Note: Couldn't add is_read column: {e}")
        print("This is OK if the column already exists.")

def downgrade() -> None:
    # This is intentionally not implemented to avoid data loss
    pass
