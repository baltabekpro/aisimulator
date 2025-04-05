"""Add is_read column to messages table

Revision ID: add_is_read_to_messages
Revises: dec32fa40317
Create Date: 2025-04-05 11:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_is_read_to_messages'
down_revision: Union[str, None] = 'dec32fa40317'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    try:
        # Check if is_read column already exists
        from sqlalchemy import inspect, MetaData, Table
        conn = op.get_bind()
        metadata = MetaData()
        messages = Table('messages', metadata, autoload_with=conn)
        
        # If is_read column doesn't exist, add it
        if 'is_read' not in [c.name for c in messages.columns]:
            op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=True, server_default='f'))
            op.execute("UPDATE messages SET is_read = false")
            op.alter_column('messages', 'is_read', nullable=False, server_default=None)
    except Exception as e:
        op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=False, server_default='f'))

def downgrade() -> None:
    op.drop_column('messages', 'is_read')
