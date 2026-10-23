"""crear tabla trabajos finalizados

Cada ONG adjudicada marca cuándo terminó su trabajo en la emergencia;
el monitoreo sólo se puede finalizar cuando todas lo marcaron.

Revision ID: a9c4e7f2b318
Revises: f3b8d1c64a72
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9c4e7f2b318'
down_revision: Union[str, Sequence[str], None] = 'f3b8d1c64a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trabajos_finalizados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('emergencia_id', sa.Integer(), nullable=False),
        sa.Column('ong_cuit', sa.String(length=32), nullable=False),
        sa.Column('usuario_id', sa.String(length=255), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['emergencia_id'], ['emergencias.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('emergencia_id', 'ong_cuit'),
    )


def downgrade() -> None:
    op.drop_table('trabajos_finalizados')
