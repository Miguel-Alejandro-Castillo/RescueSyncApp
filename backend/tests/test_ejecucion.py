from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from dependencies.bonita import get_bonita_service
from dependencies.jwt_auth import ALGORITHM, SECRET_KEY
from main import app
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta

CRUZ_ROJA = "30-54603392-5"
HUESPED = "30-63749647-2"
OTRA_ONG = "30-71250682-9"


class BonitaEnMonitoreo:
    """Caso parado en "Monitorear la ejecucion"; al completarla pasa a la tarea de las ONGs y luego termina."""

    SIGUIENTE = {
        "Monitorear la ejecucion": "Ejecutar y finalizar actividades de ayuda",
        "Ejecutar y finalizar actividades de ayuda": None,
    }

    def __init__(self, tarea_actual="Monitorear la ejecucion"):
        self.tarea_actual = tarea_actual
        self.completadas = []

    async def obtener_tareas_humanas_por_caso(self, case_id):
        return [{"id": self.tarea_actual, "name": self.tarea_actual}] if self.tarea_actual else []

    async def esperar_tareas_humanas_por_caso(self, case_id, nombre_esperado=None, **kwargs):
        return await self.obtener_tareas_humanas_por_caso(case_id)

    async def completar_tarea_humana(self, task_id, contract=None):
        self.completadas.append(task_id)
        self.tarea_actual = self.SIGUIENTE[task_id]


@pytest.fixture
def bonita(client):
    falso = BonitaEnMonitoreo()

    async def override():
        yield falso

    app.dependency_overrides[get_bonita_service] = override
    return falso


def headers_ong(cuit, user_id="20"):
    token = jwt.encode({
        "sub": f"rep_{cuit}", "user_id": user_id, "cuitONG": cuit,
        "memberships": [{"group": {"name": "ongs"}, "role": {"name": "representante_ong"}}],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }, SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def crear_emergencia_adjudicada(session):
    """Emergencia con un lote adjudicado a dos ONGs: Cruz Roja (dos representantes) y Fundación Huésped."""
    emergencia = Emergencia(usuarioCreador="1", bonitaCaseId="1001", zonaAfectada="Zona Norte",
                            nivelGravedad="alto", descripcionInicial="Inundación",
                            estado=EmergenciaEstado.ADJUDICADA)
    session.add(emergencia)
    session.flush()
    lote = Lote(emergenciaId=emergencia.id, tipoRecurso="Insumos", descripcion="Raciones de comida",
                cantidad=10, estado=LoteEstado.ADJUDICADO, fechaLimiteConvocatoria=datetime.now(timezone.utc))
    session.add(lote)
    session.flush()
    oferta = Oferta(lote_id=lote.id, ong_lider_id=12, resultado_validacion={"participantes": []})
    session.add(oferta)
    session.flush()
    participantes = [
        ParticipanteOferta(oferta_id=oferta.id, ong_id=12, ong_cuit=CRUZ_ROJA, cantidad_aportada=3),
        ParticipanteOferta(oferta_id=oferta.id, ong_id=13, ong_cuit=CRUZ_ROJA, cantidad_aportada=2),
        ParticipanteOferta(oferta_id=oferta.id, ong_id=18, ong_cuit=HUESPED, cantidad_aportada=5),
    ]
    session.add_all(participantes)
    session.flush()
    oferta.resultado_validacion = {"participantes": [
        {"participante_id": participantes[0].id, "ong_nombre": "Cruz Roja Argentina"},
        {"participante_id": participantes[2].id, "ong_nombre": "Fundación Huésped"},
    ]}
    adjudicacion = Adjudicacion(lote_id=lote.id, usuario_id="1")
    session.add(adjudicacion)
    session.flush()
    session.add_all([AdjudicacionDetalle(adjudicacion_id=adjudicacion.id, participante_oferta_id=p.id,
                                         cantidad_adjudicada=p.cantidad_aportada) for p in participantes])
    session.commit()
    return emergencia.id


def marcar(client, emergencia_id, cuit, user_id="20"):
    return client.post(f"/api/rescue/ejecucion/emergencias/{emergencia_id}/trabajo-finalizado",
                       headers=headers_ong(cuit, user_id))


def monitoreo(client, auth_headers):
    [emergencia] = client.get("/api/rescue/monitoreo", headers=auth_headers("centro_coordinador")).json()
    return emergencia


def finalizar(client, auth_headers, emergencia_id):
    return client.post(f"/api/rescue/monitoreo/emergencias/{emergencia_id}/finalizar",
                       headers=auth_headers("centro_coordinador"))


def test_la_ong_ve_lo_que_le_adjudicaron(client, session):
    emergencia_id = crear_emergencia_adjudicada(session)

    [emergencia] = client.get("/api/rescue/ejecucion/mis-emergencias", headers=headers_ong(CRUZ_ROJA)).json()

    assert emergencia["id"] == emergencia_id
    assert emergencia["en_ejecucion"] is True
    assert [l["cantidad_adjudicada"] for l in emergencia["lotes"]] == [3, 2]
    assert client.get("/api/rescue/ejecucion/mis-emergencias", headers=headers_ong(OTRA_ONG)).json() == []


def test_cualquier_representante_marca_por_su_ong_una_sola_vez(client, session):
    emergencia_id = crear_emergencia_adjudicada(session)

    assert marcar(client, emergencia_id, CRUZ_ROJA, user_id="12").status_code == 201
    repetido = marcar(client, emergencia_id, CRUZ_ROJA, user_id="13")

    assert repetido.status_code == 409


def test_una_ong_no_adjudicada_no_puede_marcar(client, session):
    emergencia_id = crear_emergencia_adjudicada(session)

    assert marcar(client, emergencia_id, OTRA_ONG).status_code == 403


def test_no_se_marca_fuera_de_la_ejecucion(client, session):
    emergencia_id = crear_emergencia_adjudicada(session)
    emergencia = session.get(Emergencia, emergencia_id)
    emergencia.estado = EmergenciaEstado.MONITOREO_FINALIZADO
    session.add(emergencia)
    session.commit()

    assert marcar(client, emergencia_id, CRUZ_ROJA).status_code == 409


def test_no_se_finaliza_el_monitoreo_hasta_que_terminen_todas(client, session, auth_headers, bonita):
    emergencia_id = crear_emergencia_adjudicada(session)
    marcar(client, emergencia_id, CRUZ_ROJA)

    estado = monitoreo(client, auth_headers)
    response = finalizar(client, auth_headers, emergencia_id)

    assert {o["nombre"]: bool(o["finalizado_en"]) for o in estado["ongs"]} == {
        "Cruz Roja Argentina": True, "Fundación Huésped": False}
    assert estado["todas_finalizaron"] is False
    assert response.status_code == 409
    assert "Fundación Huésped" in response.json()["detail"]
    assert bonita.completadas == []


def test_finalizar_monitoreo_cierra_las_tareas_de_bonita(client, session, auth_headers, bonita):
    emergencia_id = crear_emergencia_adjudicada(session)
    marcar(client, emergencia_id, CRUZ_ROJA)
    marcar(client, emergencia_id, HUESPED)

    assert monitoreo(client, auth_headers)["todas_finalizaron"] is True
    response = finalizar(client, auth_headers, emergencia_id)

    assert response.status_code == 204
    assert bonita.completadas == ["Monitorear la ejecucion", "Ejecutar y finalizar actividades de ayuda"]
    session.expire_all()
    assert session.get(Emergencia, emergencia_id).estado == EmergenciaEstado.MONITOREO_FINALIZADO


def test_finalizar_retoma_si_el_monitoreo_ya_se_habia_completado(client, session, auth_headers, bonita):
    bonita.tarea_actual = "Ejecutar y finalizar actividades de ayuda"
    emergencia_id = crear_emergencia_adjudicada(session)
    marcar(client, emergencia_id, CRUZ_ROJA)
    marcar(client, emergencia_id, HUESPED)

    response = finalizar(client, auth_headers, emergencia_id)

    assert response.status_code == 204
    assert bonita.completadas == ["Ejecutar y finalizar actividades de ayuda"]
