"""Conservar el historial de las ofertas descartadas."""

from alembic import op
import sqlalchemy as sa

revision = 'f2be79a5b401'
down_revision = 'e1a7c3b92d54'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ofertas', sa.Column('descartada_en', sa.DateTime(timezone=True)))
    op.add_column('ofertas', sa.Column('motivo_descarte', sa.String(20)))
    op.add_column('ofertas', sa.Column('tarea_bonita_descarte', sa.String(32)))
    # Para lotes ya reformulados, la creación del reemplazo documenta el descarte.
    op.execute("""
        UPDATE ofertas AS oferta
        SET descartada_en = reemplazo.creado,
            motivo_descarte = 'reformulacion'
        FROM lotes AS anterior
        JOIN (
            SELECT "loteOrigenId", MIN("fechaCreacion") AS creado
            FROM lotes WHERE "loteOrigenId" IS NOT NULL GROUP BY "loteOrigenId"
        ) AS reemplazo ON reemplazo."loteOrigenId" = anterior.id
        WHERE oferta.lote_id = anterior.id AND anterior.estado = 'reformulado'
    """)


def downgrade():
    op.drop_column('ofertas', 'tarea_bonita_descarte')
    op.drop_column('ofertas', 'motivo_descarte')
    op.drop_column('ofertas', 'descartada_en')
