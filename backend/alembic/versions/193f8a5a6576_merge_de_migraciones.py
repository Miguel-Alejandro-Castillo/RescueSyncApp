"""merge de migraciones

Revision ID: 193f8a5a6576
Revises: f2b8d4a61c37, f2be79a5b401
Create Date: 2026-11-11 18:33:22.989593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '193f8a5a6576'
down_revision: Union[str, Sequence[str], None] = ('f2b8d4a61c37', 'f2be79a5b401')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
