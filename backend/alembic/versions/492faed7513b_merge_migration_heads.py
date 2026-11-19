"""merge migration heads

Revision ID: 492faed7513b
Revises: 193f8a5a6576, 7a024f627505
Create Date: 2026-11-13 01:19:23.988614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '492faed7513b'
down_revision: Union[str, Sequence[str], None] = ('193f8a5a6576', '7a024f627505')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
