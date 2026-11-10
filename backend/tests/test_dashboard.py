from datetime import datetime, timezone

import pytest

from services.dashboard_calculos import (
    a_csv,
    calcular_resumen_casos,
    calcular_tiempos_por_etapa,
    inicio_de_casos,
    meses_anteriores,
    parsear_fecha_bonita,
    rango_mes,
)

UTC = timezone.utc


@pytest.mark.parametrize("rol", ["operador_municipal", "centro_coordinador", "representante_ong", "auditor"])
def test_solo_directivo_ve_el_dashboard(client, auth_headers, rol):
    for url in ("/api/rescue/dashboard/indicadores", "/api/rescue/dashboard/exportar"):
        assert client.get(url, headers=auth_headers(rol)).status_code == 403


def test_dashboard_sin_token_devuelve_401(client):
    assert client.get("/api/rescue/dashboard/indicadores").status_code == 401


def test_directivo_obtiene_indicadores_aunque_no_haya_datos(client, auth_headers):
    response = client.get("/api/rescue/dashboard/indicadores", headers=auth_headers("directivo"))

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["kpis"]["suministros_movilizados"] == 0
    assert cuerpo["consorcios"]["ofertas_total"] == 0
    assert len(cuerpo["suministros_por_mes"]) == 6


def test_mes_invalido_devuelve_422(client, auth_headers):
    response = client.get("/api/rescue/dashboard/indicadores?mes=2026-13", headers=auth_headers("directivo"))

    assert response.status_code == 422


def test_exportar_csv_requiere_dataset(client, auth_headers):
    response = client.get("/api/rescue/dashboard/exportar?formato=csv", headers=auth_headers("directivo"))

    assert response.status_code == 422


def test_exportar_csv_de_proyectos(client, auth_headers):
    response = client.get(
        "/api/rescue/dashboard/exportar?formato=csv&dataset=proyectos",
        headers=auth_headers("directivo"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]


def test_parsear_fecha_bonita():
    assert parsear_fecha_bonita("2026-11-03 10:30:00.123") == datetime(2026, 11, 3, 10, 30, 0, 123000, tzinfo=UTC)
    assert parsear_fecha_bonita("2026-11-03 10:30:00") == datetime(2026, 11, 3, 10, 30, tzinfo=UTC)
    assert parsear_fecha_bonita(None) is None
    assert parsear_fecha_bonita("basura") is None


def test_rango_mes_cruza_el_fin_de_anio():
    desde, hasta = rango_mes("2026-12")

    assert desde == datetime(2026, 12, 1, tzinfo=UTC)
    assert hasta == datetime(2027, 1, 1, tzinfo=UTC)
    assert rango_mes(None) == (None, None)
    with pytest.raises(ValueError):
        rango_mes("12/2026")


def test_meses_anteriores():
    assert meses_anteriores(datetime(2026, 2, 10, tzinfo=UTC), 3) == ["2025-12", "2026-01", "2026-02"]


def test_tiempos_por_etapa_miden_desde_la_tarea_anterior():
    casos = [{"id": "1", "start": "2026-11-01 08:00:00.000"}]
    tareas = [
        {"caseId": "1", "name": "Generar lotes de necesidades", "reached_state_date": "2026-11-01 12:00:00.000"},
        {"caseId": "1", "name": "Registrar  emergencia", "reached_state_date": "2026-11-01 10:00:00.000"},
        {"caseId": "99", "name": "Registrar emergencia", "reached_state_date": "2026-11-01 10:00:00.000"},
    ]

    etapas = calcular_tiempos_por_etapa(tareas, inicio_de_casos(casos, []))

    assert [(e["etapa"], e["promedio_horas"]) for e in etapas] == [
        ("Registrar emergencia", 2.0),
        ("Generar lotes de necesidades", 2.0),
    ]


def test_tiempos_por_etapa_promedian_varios_casos_y_filtran_mes():
    casos = [
        {"id": "1", "start": "2026-10-31 00:00:00.000"},
        {"id": "2", "start": "2026-11-02 00:00:00.000"},
    ]
    tareas = [
        {"caseId": "1", "name": "Registrar emergencia", "reached_state_date": "2026-10-31 02:00:00.000"},
        {"caseId": "2", "name": "Registrar emergencia", "reached_state_date": "2026-11-02 06:00:00.000"},
    ]
    desde, hasta = rango_mes("2026-11")

    etapas = calcular_tiempos_por_etapa(tareas, inicio_de_casos(casos, []), desde, hasta)

    assert etapas[0]["promedio_horas"] == 6.0
    assert etapas[0]["muestras"] == 1


def test_resumen_de_casos():
    abiertos = [{"id": "5", "start": "2026-11-01 00:00:00.000"}]
    archivados = [
        {"id": "9", "sourceObjectId": "1", "state": "completed", "start": "2026-11-01 00:00:00.000", "end_date": "2026-11-02 00:00:00.000"},
        {"id": "10", "sourceObjectId": "2", "state": "cancelled", "start": "2026-11-01 00:00:00.000", "end_date": "2026-11-02 00:00:00.000"},
    ]

    assert calcular_resumen_casos(abiertos, archivados) == {
        "en_curso": 1,
        "finalizados": 1,
        "duracion_promedio_horas": 24.0,
    }


def test_a_csv_incluye_encabezado_y_filas():
    texto = a_csv(["tipo", "cantidad"], [{"tipo": "Insumos", "cantidad": 5, "extra": "x"}])

    assert texto.splitlines() == ["tipo,cantidad", "Insumos,5"]
