"""decision del coordinador por emergencia

La acción ante cobertura insuficiente se decide una vez por emergencia
(única tarea "Evaluar acciones a tomar" del caso en Bonita), no por oferta.

Revision ID: f3b8d1c64a72
Revises: e1a7c3b92d54
Create Date: 2026-10-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3b8d1c64a72'
down_revision: Union[str, Sequence[str], None] = 'e1a7c3b92d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('emergencias', sa.Column('decisionesCoordinador', sa.JSON(), nullable=False, server_default='[]'))
    op.drop_column('ofertas', 'accion_tomada')


def downgrade() -> None:
    op.add_column('ofertas', sa.Column('accion_tomada', sa.String(length=20), nullable=True))
    op.drop_column('emergencias', 'decisionesCoordinador')
