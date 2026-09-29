from sqlmodel import select

from models.emergencia import Emergencia


def test_post_emergencia_se_guarda_en_la_bd(client, session, auth_headers):
    payload = {
        "zonaAfectada": "Zona Norte",
        "nivelGravedad": "alto",
        "descripcionInicial": "Inundacion en el barrio",
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
