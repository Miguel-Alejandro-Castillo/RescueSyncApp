"""agregar accion tomada en ofertas

Revision ID: b7d2e41f9c08
Revises: a3f1c9d27b45
Create Date: 2026-10-13 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d2e41f9c08'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d27b45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ofertas', sa.Column('accion_tomada', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('ofertas', 'accion_tomada')
