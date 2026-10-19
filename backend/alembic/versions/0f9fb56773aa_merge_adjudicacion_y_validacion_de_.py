"""merge adjudicacion y validacion de ofertas

Revision ID: 0f9fb56773aa
Revises: 61cc3618ce0a, e6a102b7d902
Create Date: 2026-10-19 14:58:25.861966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0f9fb56773aa'
down_revision: Union[str, Sequence[str], None] = ('61cc3618ce0a', 'e6a102b7d902')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
