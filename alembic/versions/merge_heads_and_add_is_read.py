"""Merge multiple heads and add is_read column

Revision ID: merge_heads_add_is_read
Revises: dec32fa40317, add_is_read_column
Create Date: 2025-04-05 12:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_heads_add_is_read'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = ('dec32fa40317', 'add_is_read_column')

def upgrade() -> None:
    # This is a merge migration, so we add the is_read column directly
    try:
        # Check if we're using SQLite
        conn = op.get_bind()
        is_sqlite = 'sqlite' in conn.engine.name.lower()
        
        # Check if the column already exists
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('messages')]
        
        if 'is_read' not in columns:
            if is_sqlite:
                op.add_column('messages', sa.Column('is_read', sa.Boolean(), 
                                                   nullable=False, server_default='0'))
            else:
                op.add_column('messages', sa.Column('is_read', sa.Boolean(), 
                                                   nullable=False, server_default='false'))
            print("Added is_read column to messages table")
    except Exception as e:
        print(f"Note: Could not add is_read column: {e}")
        print("This is OK if the column already exists.")

def downgrade() -> None:
    # No downgrade for merges to avoid data loss
    pass
