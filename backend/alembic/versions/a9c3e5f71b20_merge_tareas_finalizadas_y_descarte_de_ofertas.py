"""merge tareas finalizadas y descarte de ofertas

Revision ID: a9c3e5f71b20
Revises: f2b8d4a61c37, f2be79a5b401
Create Date: 2026-11-17 12:00:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'a9c3e5f71b20'
down_revision: Union[str, Sequence[str], None] = ('f2b8d4a61c37', 'f2be79a5b401')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Solo une las dos ramas de migraciones; no cambia el esquema.
    pass


def downgrade() -> None:
    pass
