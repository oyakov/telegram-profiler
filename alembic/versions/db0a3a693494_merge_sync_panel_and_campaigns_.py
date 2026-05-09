"""merge sync panel and campaigns migrations

Revision ID: db0a3a693494
Revises: o0p1q2r3s4, p0q1r2s3t4
Create Date: 2026-05-09 21:39:03.201844
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'db0a3a693494'
down_revision: Union[str, None] = ('o0p1q2r3s4', 'p0q1r2s3t4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
