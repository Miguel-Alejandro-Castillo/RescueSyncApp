from datetime import datetime, timedelta, timezone
from jose import jwt
from dependencies.jwt_auth import SECRET_KEY, ALGORITHM
from models.emergencia import Emergencia
from models.lote import Lote


def test_cada_ong_ve_solo_lotes_sin_oferta_propia(client, session, auth_headers):
    now = datetime.now(timezone.utc)
    session.add(Emergencia(id=1, zonaAfectada='Prueba', nivelGravedad='alto',
                          descripcionInicial='Prueba', estado='publicada', usuarioCreador='1'))
    session.commit()
    for id in [1, 2, 3]:
        session.add(Lote(id=id, emergenciaId=1, tipoRecurso='Insumos', descripcion='Agua',
                         cantidad=10, estado='activo', fechaLimiteConvocatoria=now + timedelta(days=1)))
    session.commit()
    own = auth_headers('representante_ong')
    other = {'Authorization': 'Bearer ' + jwt.encode({
        'sub': 'otra_ong', 'user_id': '2', 'exp': now + timedelta(minutes=5),
        'memberships': [{'role': {'name': 'representante_ong'}}],
    }, SECRET_KEY, algorithm=ALGORITHM)}
    for id in [1, 2, 3]:
        response = client.post('/api/rescue/ofertas/', headers=own,
                               json={'id_lote': id, 'id_ong': 999, 'cant_recurso': 1})
        assert response.status_code == 201
        assert response.json()['id_ong'] == 1
        expected = set(range(id + 1, 4))
        lots = client.get('/api/rescue/emergencias/1/lotes', headers=own)
        assert lots.status_code == 200
        assert {lot['id'] for lot in lots.json()} == expected
        portal = client.get('/api/rescue/ofertas/emergencias-disponibles', headers=own).json()
        assert ({lot['id'] for lot in portal[0]['lotes']} if portal else set()) == expected
    assert len(client.get('/api/rescue/ofertas/misofertas', headers=own).json()) == 3
    assert client.get('/api/rescue/ofertas/misofertas', headers=other).json() == []
    assert len(client.get('/api/rescue/emergencias/1/lotes', headers=other).json()) == 3
    assert client.put(f"/api/rescue/ofertas/{response.json()['id']}", headers=other,
                      json={'id_ong': 1, 'cant_recurso': 2}).status_code == 403
