"""Fijar la ONG de origen del aporte sin consultar identidades actuales."""
import json
from alembic import op
import sqlalchemy as sa

revision = 'e6a102b7d902'
down_revision = 'd5f021a6c901'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('participantes_oferta', sa.Column('ong_cuit', sa.String(32), nullable=True))
    connection = op.get_bind()
    # Solo recuperar identidades ya registradas en el resultado histórico.
    # Sin evidencia se conserva NULL: nunca inferirlo del perfil actual de Bonita.
    rows = connection.execute(sa.text(
        'SELECT id, resultado_validacion FROM ofertas WHERE resultado_validacion IS NOT NULL'
    )).all()
    for oferta_id, raw in rows:
        resultado = json.loads(raw) if isinstance(raw, str) else raw
        candidatos = {}
        for detalle in (resultado or {}).get('participantes', []):
            pid, uid, cuit = detalle.get('participante_id'), detalle.get('ong_id'), detalle.get('cuit')
            if pid is not None and uid is not None and isinstance(cuit, str) and 0 < len(cuit.strip()) <= 32:
                candidatos.setdefault((pid, uid), set()).add(cuit.strip())
        for (pid, uid), cuits in candidatos.items():
            if len(cuits) == 1:
                connection.execute(sa.text(
                    'UPDATE participantes_oferta SET ong_cuit=:cuit '
                    'WHERE id=:pid AND oferta_id=:oferta AND ong_id=:uid '
                    'AND cantidad_aportada IS NOT NULL AND ong_cuit IS NULL'
                ), {'cuit': next(iter(cuits)), 'pid': pid, 'oferta': oferta_id, 'uid': uid})


def downgrade():
    op.drop_column('participantes_oferta', 'ong_cuit')
