"""Add project_id and folder_id fields for single-database architecture

This migration adds project_id to track messages/contacts by project instead of using
separate databases. Also adds folder_id to messages for quick folder lookup.

Revision ID: j5k6l7m8n9
Revises: i9j0k1l2m3n4
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "j5k6l7m8n9"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update system_projects table
    # Remove db_name column, add telegram_folder_id
    op.add_column('system_projects', sa.Column('telegram_folder_id', sa.String(100), nullable=True))
    op.create_index('idx_project_telegram_folder_id', 'system_projects', ['telegram_folder_id'])

    # 2. Update tracked_folders table
    # Add project_id (required), telegram_folder_id, and remove unique constraint on name
    op.add_column('tracked_folders', sa.Column('project_id', sa.UUID(), nullable=True))
    op.add_column('tracked_folders', sa.Column('telegram_folder_id', sa.String(100), nullable=True))
    op.create_foreign_key('fk_tracked_folders_project_id', 'tracked_folders', 'system_projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_folder_project_id', 'tracked_folders', ['project_id'])
    op.create_index('idx_folder_telegram_folder_id', 'tracked_folders', ['telegram_folder_id'])
    op.drop_constraint('tracked_folders_name_key', 'tracked_folders', type_='unique')

    # 3. Update contacts table
    # Add project_id
    op.add_column('contacts', sa.Column('project_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_contacts_project_id', 'contacts', 'system_projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_contacts_project_id', 'contacts', ['project_id'])

    # 4. Update messages table
    # Add project_id and folder_id
    op.add_column('messages', sa.Column('project_id', sa.UUID(), nullable=True))
    op.add_column('messages', sa.Column('folder_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_messages_project_id', 'messages', 'system_projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_messages_folder_id', 'messages', 'tracked_folders', ['folder_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_messages_project_id', 'messages', ['project_id'])
    op.create_index('idx_messages_folder_id', 'messages', ['folder_id'])

    # 5. Update voice_notes table
    # Add project_id
    op.add_column('voice_notes', sa.Column('project_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_voice_notes_project_id', 'voice_notes', 'system_projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_voice_notes_project_id', 'voice_notes', ['project_id'])

    # 6. Remove unique constraint on contacts email (contacts can be in multiple projects)
    try:
        op.drop_constraint('contacts_email_key', 'contacts', type_='unique')
    except:
        pass  # Constraint might not exist or have different name


def downgrade() -> None:
    # Remove all added columns and indexes in reverse order
    op.drop_index('idx_voice_notes_project_id', table_name='voice_notes')
    op.drop_constraint('fk_voice_notes_project_id', 'voice_notes', type_='foreignkey')
    op.drop_column('voice_notes', 'project_id')

    op.drop_index('idx_messages_folder_id', table_name='messages')
    op.drop_index('idx_messages_project_id', table_name='messages')
    op.drop_constraint('fk_messages_folder_id', 'messages', type_='foreignkey')
    op.drop_constraint('fk_messages_project_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'folder_id')
    op.drop_column('messages', 'project_id')

    op.drop_index('idx_contacts_project_id', table_name='contacts')
    op.drop_constraint('fk_contacts_project_id', 'contacts', type_='foreignkey')
    op.drop_column('contacts', 'project_id')

    op.drop_index('idx_folder_telegram_folder_id', table_name='tracked_folders')
    op.drop_index('idx_folder_project_id', table_name='tracked_folders')
    op.drop_constraint('fk_tracked_folders_project_id', 'tracked_folders', type_='foreignkey')
    op.drop_column('tracked_folders', 'telegram_folder_id')
    op.drop_column('tracked_folders', 'project_id')

    op.drop_index('idx_project_telegram_folder_id', table_name='system_projects')
    op.drop_column('system_projects', 'telegram_folder_id')
