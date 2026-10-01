from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from models.emergencia import Emergencia

INICIO = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

# Ventana de tiempo en modo demo (calcular_fecha_limite_demo en routers/lote.py)
PLAZOS = {
    "critico": timedelta(minutes=2),
    "alto": timedelta(minutes=4),
    "medio": timedelta(minutes=6),
    "bajo": timedelta(minutes=8),
}


def crear_lote(client, session, auth_headers, nivel_gravedad):
    emergencia = Emergencia(
        usuarioCreador="1",
        bonitaCaseId="1001",
        zonaAfectada="Zona Norte",
        nivelGravedad=nivel_gravedad,
        descripcionInicial="Inundacion en el barrio",
    )
    session.add(emergencia)
    session.commit()
    session.refresh(emergencia)

    response = client.post(
        "/api/rescue/lotes",
        json={
            "emergenciaId": emergencia.id,
            "lotes": [{"tipoRecurso": "Insumos", "descripcion": "Agua", "cantidad": 10}],
        },
        headers=auth_headers("centro_coordinador"),
    )
    assert response.status_code == 201
    return response.json()[0]


def ofertar(client, auth_headers, lote_id):
    return client.post(
        "/api/rescue/ofertas/",
        json={"id_lote": lote_id, "id_ong": 1, "cant_recurso": 1},
        headers=auth_headers("representante_ong"),
    )


@pytest.mark.parametrize("nivel_gravedad, plazo", PLAZOS.items())
def test_lote_guarda_fecha_limite_segun_gravedad(client, session, auth_headers, nivel_gravedad, plazo):
    with freeze_time(INICIO):
        lote = crear_lote(client, session, auth_headers, nivel_gravedad)

    fecha_limite = datetime.fromisoformat(lote["fechaLimiteConvocatoria"])
    if fecha_limite.tzinfo is None:
        fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)

    assert fecha_limite == INICIO + plazo


@pytest.mark.parametrize("nivel_gravedad, plazo", PLAZOS.items())
def test_oferta_dentro_del_plazo_se_acepta(client, session, auth_headers, nivel_gravedad, plazo):
    with freeze_time(INICIO) as reloj:
        lote = crear_lote(client, session, auth_headers, nivel_gravedad)

        reloj.move_to(INICIO + plazo - timedelta(seconds=30))
        response = ofertar(client, auth_headers, lote["id"])

    assert response.status_code == 201


@pytest.mark.parametrize("nivel_gravedad, plazo", PLAZOS.items())
def test_oferta_fuera_del_plazo_se_rechaza(client, session, auth_headers, nivel_gravedad, plazo):
    with freeze_time(INICIO) as reloj:
        lote = crear_lote(client, session, auth_headers, nivel_gravedad)

        reloj.move_to(INICIO + plazo + timedelta(seconds=1))
        response = ofertar(client, auth_headers, lote["id"])

    assert response.status_code == 400
    assert "expirado" in response.json()["detail"]


def test_oferta_justo_en_el_limite_se_acepta(client, session, auth_headers):
    with freeze_time(INICIO) as reloj:
        lote = crear_lote(client, session, auth_headers, "bajo")

        reloj.move_to(INICIO + PLAZOS["bajo"])
        response = ofertar(client, auth_headers, lote["id"])

    assert response.status_code == 201
