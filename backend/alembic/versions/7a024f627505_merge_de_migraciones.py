"""merge de migraciones

Revision ID: 7a024f627505
Revises: f2b8d4a61c37, f2be79a5b401
Create Date: 2026-11-10 22:35:00.602528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '7a024f627505'
down_revision: Union[str, Sequence[str], None] = ('f2b8d4a61c37', 'f2be79a5b401')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
