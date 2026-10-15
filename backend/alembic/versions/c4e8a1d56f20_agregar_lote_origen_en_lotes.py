"""agregar lote origen en lotes

Revision ID: c4e8a1d56f20
Revises: b7d2e41f9c08
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e8a1d56f20'
down_revision: Union[str, Sequence[str], None] = 'b7d2e41f9c08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lotes', sa.Column('loteOrigenId', sa.Integer(), nullable=True))
    op.create_foreign_key('lotes_loteOrigenId_fkey', 'lotes', 'lotes', ['loteOrigenId'], ['id'])


def downgrade() -> None:
    op.drop_constraint('lotes_loteOrigenId_fkey', 'lotes', type_='foreignkey')
    op.drop_column('lotes', 'loteOrigenId')
