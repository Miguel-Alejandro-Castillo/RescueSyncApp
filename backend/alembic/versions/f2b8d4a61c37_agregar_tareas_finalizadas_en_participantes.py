"""agregar tareas finalizadas en participantes

Revision ID: f2b8d4a61c37
Revises: e1a7c3b92d54
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2b8d4a61c37'
down_revision: Union[str, Sequence[str], None] = 'e1a7c3b92d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('participantes_oferta', sa.Column('tareas_finalizadas', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('participantes_oferta', 'tareas_finalizadas')
