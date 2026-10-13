"""agregar campo valida en ofertas

Revision ID: a3f1c9d27b45
Revises: ebe3048d8d56
Create Date: 2026-10-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f1c9d27b45'
down_revision: Union[str, Sequence[str], None] = 'ebe3048d8d56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ofertas', sa.Column('valida', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('ofertas', 'valida')
