"""Persistir el resultado de validación de recursos al cerrar la convocatoria."""
from alembic import op
import sqlalchemy as sa

revision = 'd5f021a6c901'
down_revision = 'c4e8a1d56f20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('lotes', sa.Column('recurso_codigo', sa.String(100), nullable=True))
    op.add_column('ofertas', sa.Column('estado_validacion', sa.String(20), nullable=False, server_default='pendiente'))
    op.add_column('ofertas', sa.Column('validada_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ofertas', sa.Column('ventana_validada', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ofertas', sa.Column('resultado_validacion', sa.JSON(), nullable=True))


def downgrade():
    for name in ('resultado_validacion', 'ventana_validada', 'validada_en', 'estado_validacion'):
        op.drop_column('ofertas', name)
    op.drop_column('lotes', 'recurso_codigo')
