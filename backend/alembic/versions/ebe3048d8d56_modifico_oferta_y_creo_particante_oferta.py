"""modifico oferta y creo particante_oferta

Revision ID: ebe3048d8d56
Revises: 80897f29c582
Create Date: 2026-10-11 03:41:08.789458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ebe3048d8d56'
down_revision: Union[str, Sequence[str], None] = '80897f29c582'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear la nueva tabla de participantes
    op.create_table(
        'participantes_oferta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('oferta_id', sa.Integer(), nullable=False),
        sa.Column('ong_id', sa.Integer(), nullable=False),
        sa.Column('cantidad_aportada', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['oferta_id'], ['ofertas.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Agregar las nuevas columnas requeridas directamente
    op.add_column('ofertas', sa.Column('lote_id', sa.Integer(), nullable=False))
    op.add_column('ofertas', sa.Column('ong_lider_id', sa.Integer(), nullable=False))
    op.add_column('ofertas', sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

    # 3. Eliminar las columnas viejas que ya no se usan
    op.drop_column('ofertas', 'cant_recurso')
    op.drop_column('ofertas', 'id_lote')
    op.drop_column('ofertas', 'id_ong')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('ofertas', sa.Column('id_ong_creadora', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('ofertas', sa.Column('id_lote', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('ofertas', sa.Column('ongs_ids', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False))
    op.add_column('ofertas', sa.Column('es_consorcio', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('ofertas', sa.Column('cant_recurso', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'ofertas', type_='foreignkey')
    op.create_foreign_key(op.f('ofertas_id_lote_fkey'), 'ofertas', 'lotes', ['id_lote'], ['id'])
    op.drop_column('ofertas', 'fecha_creacion')
    op.drop_column('ofertas', 'ong_lider_id')
    op.drop_column('ofertas', 'lote_id')
    op.drop_table('participantes_oferta')
