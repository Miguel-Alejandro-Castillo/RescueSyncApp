from sqlmodel import select

from models.emergencia import Emergencia


def test_post_emergencia_se_guarda_en_la_bd(client, session, auth_headers):
    payload = {
        "zonaAfectada": "Zona Norte",
        "nivelGravedad": "alto",
        "descripcionInicial": "Inundacion en el barrio",
        "usuarioCreador": "usuario_falsificado",
    }

    response = client.post(
        "/api/rescue/emergencias",
        json=payload,
        headers=auth_headers("operador_municipal"),
    )

    assert response.status_code == 200

    guardadas = session.exec(select(Emergencia)).all()

    assert len(guardadas) == 1
    assert guardadas[0].zonaAfectada == "Zona Norte"
    assert guardadas[0].nivelGravedad == "alto"
    assert guardadas[0].descripcionInicial == "Inundacion en el barrio"
    assert guardadas[0].estado == "creada"
    assert guardadas[0].id is not None
    assert guardadas[0].fechaCreacion is not None
    assert guardadas[0].usuarioCreador == "1"


def test_no_publica_lotes_sin_caso_bonita(client, session, auth_headers):
    from models.lote import Lote
    emergencia = Emergencia(zonaAfectada='Demo', nivelGravedad='alto',
                            descripcionInicial='Sin caso', usuarioCreador='sin_registro')
    session.add(emergencia)
    session.commit()
    session.refresh(emergencia)
    response = client.post('/api/rescue/lotes', headers=auth_headers('centro_coordinador'),
                           json={'emergenciaId': emergencia.id, 'lotes': [
                               {'tipoRecurso': 'Insumos', 'descripcion': 'Agua', 'cantidad': 10}
                           ]})
    assert response.status_code == 409
    assert 'caso asociado en Bonita' in response.json()['detail']
    assert session.exec(select(Lote)).all() == []
