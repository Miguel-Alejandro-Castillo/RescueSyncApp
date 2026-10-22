"""crear tabla eventos ejecucion

Revision ID: e1a7c3b92d54
Revises: 0f9fb56773aa
Create Date: 2026-10-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1a7c3b92d54'
down_revision: Union[str, Sequence[str], None] = '0f9fb56773aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'eventos_ejecucion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lote_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.String(length=255), nullable=False),
        sa.Column('descripcion', sa.String(length=500), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['lote_id'], ['lotes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('eventos_ejecucion')
