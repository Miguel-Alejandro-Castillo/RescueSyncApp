import pytest

EMERGENCIA = {
    "zonaAfectada": "Zona Norte",
    "nivelGravedad": "alto",
    "descripcionInicial": "Inundacion en el barrio",
}


@pytest.mark.parametrize("metodo, url", [
    ("get", "/api/rescue/emergencias"),
    ("get", "/api/rescue/emergencias/1"),
    ("post", "/api/rescue/emergencias"),
    ("delete", "/api/rescue/emergencias/1"),
    ("get", "/api/rescue/emergencias/1/lotes"),
    ("get", "/api/rescue/lotes"),
    ("get", "/api/rescue/lotes/1"),
    ("post", "/api/rescue/lotes"),
    ("delete", "/api/rescue/lotes/1"),
    ("get", "/api/rescue/ofertas/emergencias-disponibles"),
    ("post", "/api/rescue/ofertas/"),
])
def test_sin_token_devuelve_401(client, metodo, url):
    response = getattr(client, metodo)(url)

    assert response.status_code == 401


def test_token_invalido_devuelve_401(client):
    response = client.get(
        "/api/rescue/emergencias",
        headers={"Authorization": "Bearer token-trucho"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("rol", ["centro_coordinador", "representante_ong", "auditor", "directivo"])
def test_solo_operador_municipal_crea_emergencias(client, auth_headers, rol):
    response = client.post("/api/rescue/emergencias", json=EMERGENCIA, headers=auth_headers(rol))

    assert response.status_code == 403


@pytest.mark.parametrize("rol", ["operador_municipal", "representante_ong", "auditor"])
def test_solo_centro_coordinador_crea_lotes(client, auth_headers, rol):
    payload = {"emergenciaId": 1, "lotes": []}

    response = client.post("/api/rescue/lotes", json=payload, headers=auth_headers(rol))

    assert response.status_code == 403


@pytest.mark.parametrize("rol", ["operador_municipal", "centro_coordinador", "auditor"])
def test_solo_ong_crea_ofertas(client, auth_headers, rol):
    response = client.post("/api/rescue/ofertas/", json={}, headers=auth_headers(rol))

    assert response.status_code == 403


def test_ong_no_ve_listado_de_emergencias(client, auth_headers):
    response = client.get("/api/rescue/emergencias", headers=auth_headers("representante_ong"))

    assert response.status_code == 403


@pytest.mark.parametrize("url", [
    "/api/rescue/emergencias",
    "/api/rescue/lotes",
    "/api/rescue/ofertas/emergencias-disponibles",
])
@pytest.mark.parametrize("rol", ["auditor", "directivo"])
def test_auditor_puede_leer_todo(client, auth_headers, rol, url):
    response = client.get(url, headers=auth_headers(rol))

    assert response.status_code == 200


@pytest.mark.parametrize("metodo, url", [
    ("delete", "/api/rescue/emergencias/1"),
    ("delete", "/api/rescue/lotes/1"),
])
def test_auditor_no_puede_borrar(client, auth_headers, metodo, url):
    response = getattr(client, metodo)(url, headers=auth_headers("auditor"))

    assert response.status_code == 403
