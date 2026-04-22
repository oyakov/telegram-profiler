"""resize_embeddings_to_1024

Revision ID: 838dab9031a1
Revises: 5f5e4a743410
Create Date: 2026-04-16 13:38:36.791738
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector

# revision identifiers, used by Alembic.
revision: str = '838dab9031a1'
down_revision: Union[str, None] = '5f5e4a743410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Clear existing data since we are switching models/dimensions
    op.execute("UPDATE contacts SET embedding = NULL")
    op.execute("DELETE FROM message_embeddings")

    # 2. Resize columns using raw SQL for pgvector compatibility
    op.execute("ALTER TABLE contacts ALTER COLUMN embedding TYPE vector(1024)")
    op.execute("ALTER TABLE message_embeddings ALTER COLUMN embedding TYPE vector(1024)")

def downgrade() -> None:
    op.execute("UPDATE contacts SET embedding = NULL")
    op.execute("DELETE FROM message_embeddings")
    op.execute("ALTER TABLE contacts ALTER COLUMN embedding TYPE vector(768)")
    op.execute("ALTER TABLE message_embeddings ALTER COLUMN embedding TYPE vector(768)")
