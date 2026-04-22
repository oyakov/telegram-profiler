"""add message contact association

Revision ID: b749d28e8331
Revises: 6707bc82e388
Create Date: 2026-04-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b749d28e8331'
down_revision: Union[str, None] = '6707bc82e388'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create message_contacts table
    op.create_table(
        'message_contacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('contact_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'contact_id', 'role', name='uq_message_contact_role')
    )
    
    # Create indexes
    op.create_index('idx_msg_contact_contact_id', 'message_contacts', ['contact_id'], unique=False)
    op.create_index('idx_msg_contact_message_id', 'message_contacts', ['message_id'], unique=False)
    op.create_index('idx_msg_contact_role', 'message_contacts', ['role'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_msg_contact_role', table_name='message_contacts')
    op.drop_index('idx_msg_contact_message_id', table_name='message_contacts')
    op.drop_index('idx_msg_contact_contact_id', table_name='message_contacts')
    op.drop_table('message_contacts')
