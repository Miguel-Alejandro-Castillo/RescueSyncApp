"""merge migrations

Revision ID: a84b952525eb
Revises: 492faed7513b, a9c3e5f71b20
Create Date: 2026-11-20 18:50:07.151601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a84b952525eb'
down_revision: Union[str, Sequence[str], None] = ('492faed7513b', 'a9c3e5f71b20')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
