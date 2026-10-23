from datetime import datetime, timedelta, timezone

import pytest

from dependencies.bonita import get_bonita_service
from main import app
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta

AHORA = datetime.now(timezone.utc)


class BonitaEnEvaluacion:
    """Caso parado en "Evaluar acciones a tomar"; registra lo que el backend le pide a Bonita."""

    def __init__(self, tarea_actual="Evaluar acciones a tomar"):
        self.tarea_actual = tarea_actual
        self.falla_liberacion = False
        self.fallidas = []
        self.acciones = []
        self.completadas = []

    async def obtener_tareas_humanas_por_caso(self, case_id):
        return [{"id": "10", "name": self.tarea_actual}] if self.tarea_actual else []

    async def obtener_tareas_humanas_fallidas_por_caso(self, case_id):
        return self.fallidas

    async def resolver_accion_coordinador(self, case_id, accion, lote_id=None):
        self.acciones.append((accion, lote_id))
        if self.falla_liberacion:
            # Bonita acepta la tarea, pero su script de liberación falla después.
            self.fallidas = [{"id": "9", "name": self.tarea_actual}]
            self.tarea_actual = None
            return
        self.tarea_actual = {
            "PUBLICAR_CONVOCATORIA": "Cargar ofertas de  ayuda",
            "GENERAR_LOTES": "Generar lotes de necesidades",
            "ACEPTAR_OFERTAS": "Adjudicar ofertas y notificar a ONGs",
        }[accion]

    async def set_case_variable(self, *args):
        return None

    async def completar_tarea_humana(self, task_id, contract=None):
        self.completadas.append(task_id)


@pytest.fixture
def bonita(client):
    falso = BonitaEnEvaluacion()

    async def override():
        yield falso

    app.dependency_overrides[get_bonita_service] = override
    return falso


def crear_emergencia(session, cierre=AHORA - timedelta(minutes=1)):
    """Emergencia con dos lotes: uno cubierto y otro con una oferta inválida con respaldo parcial."""
    emergencia = Emergencia(usuarioCreador="1", bonitaCaseId="1001", zonaAfectada="Zona Norte",
                            nivelGravedad="alto", descripcionInicial="Inundación",
                            estado=EmergenciaEstado.PUBLICADA)
    session.add(emergencia)
    session.flush()
    cubierto = Lote(emergenciaId=emergencia.id, tipoRecurso="Insumos", descripcion="Agua",
                    cantidad=10, fechaLimiteConvocatoria=cierre)
    faltante = Lote(emergenciaId=emergencia.id, tipoRecurso="Personal", descripcion="Medicos",
                    cantidad=5, fechaLimiteConvocatoria=cierre)
    session.add_all([cubierto, faltante])
    session.flush()

    for lote, valida, verificada, cobertura in (
        (cubierto, True, 10, dict(ofertado_valido=10, faltante=0, cubierto=True)),
        (faltante, False, 2, dict(ofertado_valido=0, faltante=5, cubierto=False)),
    ):
        oferta = Oferta(lote_id=lote.id, ong_lider_id=1, valida=valida,
                        estado_validacion="valida" if valida else "invalida", validada_en=AHORA,
                        resultado_validacion={
                            "valida": valida, "cantidad_verificada": verificada,
                            "participantes": [{"participante_id": 1, "cantidad_verificada": verificada}],
                            "cobertura_lote": dict(lote_id=lote.id, requerido=lote.cantidad, completa=True,
                                                   cantidad_ofertada=lote.cantidad, **cobertura),
                        })
        session.add(oferta)
        session.flush()
        session.add(ParticipanteOferta(oferta_id=oferta.id, ong_id=1, ong_cuit="20-1",
                                       cantidad_aportada=lote.cantidad))
    session.commit()
    return emergencia.id, cubierto.id, faltante.id


def decidir(client, auth_headers, emergencia_id, **payload):
    return client.post(f"/api/rescue/emergencias/{emergencia_id}/decision", json=payload,
                       headers=auth_headers("centro_coordinador"))


def test_lista_la_emergencia_completa_para_evaluar(client, session, auth_headers, bonita):
    emergencia_id, cubierto_id, faltante_id = crear_emergencia(session)

    response = client.get("/api/rescue/emergencias/pendientes-decision",
                          headers=auth_headers("centro_coordinador"))

    assert response.status_code == 200
    [emergencia] = response.json()
    assert emergencia["id"] == emergencia_id
    lotes = {lote["id"]: lote for lote in emergencia["lotes"]}
    assert lotes[cubierto_id]["cubierto"] is True
    assert lotes[faltante_id]["faltante"] == 5
    # Se ven todas las ofertas, válidas e inválidas.
    assert [o["valida"] for o in lotes[cubierto_id]["ofertas"] + lotes[faltante_id]["ofertas"]] == [True, False]


def test_no_se_evalua_mientras_queda_tiempo_para_ofertar(client, session, auth_headers, bonita):
    emergencia_id, _, faltante_id = crear_emergencia(session, cierre=AHORA + timedelta(seconds=5))

    listado = client.get("/api/rescue/emergencias/pendientes-decision",
                         headers=auth_headers("centro_coordinador"))
    response = decidir(client, auth_headers, emergencia_id, accion="reabrir", lotes=[faltante_id])

    assert listado.json() == []
    assert response.status_code == 409
    assert "todavía está abierta" in response.json()["detail"]
    assert bonita.acciones == []


def test_no_se_evalua_si_bonita_no_espera_la_decision(client, session, auth_headers, bonita):
    bonita.tarea_actual = None  # Todavía se están validando las ofertas
    emergencia_id, _, faltante_id = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="reabrir", lotes=[faltante_id])

    assert response.status_code == 409
    assert bonita.acciones == []


def test_cobertura_parcial_es_una_sola_decision_para_la_emergencia(client, session, auth_headers, bonita):
    emergencia_id, _, faltante_id = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="parcial")

    assert response.status_code == 200
    assert bonita.acciones == [("ACEPTAR_OFERTAS", None)]
    oferta = session.query(Oferta).filter(Oferta.lote_id == faltante_id).one()
    assert oferta.resultado_validacion["cantidad_aceptada"] == 2
    emergencia = session.get(Emergencia, emergencia_id)
    assert [d["accion"] for d in emergencia.decisionesCoordinador] == ["parcial"]

    # La tarea ya no está esperando: una segunda decisión se rechaza.
    assert decidir(client, auth_headers, emergencia_id, accion="parcial").status_code == 409


def test_reabrir_solo_los_lotes_elegidos(client, session, auth_headers, bonita):
    emergencia_id, cubierto_id, faltante_id = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="reabrir", lotes=[faltante_id])

    assert response.status_code == 200
    assert bonita.acciones == [("PUBLICAR_CONVOCATORIA", faltante_id)]
    session.expire_all()
    reabierto, intacto = session.get(Lote, faltante_id), session.get(Lote, cubierto_id)
    assert reabierto.fechaLimiteConvocatoria.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
    assert intacto.fechaLimiteConvocatoria.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
    oferta = session.query(Oferta).filter(Oferta.lote_id == faltante_id).one()
    assert oferta.estado_validacion == "pendiente"


def test_no_se_puede_reabrir_un_lote_cubierto(client, session, auth_headers, bonita):
    emergencia_id, cubierto_id, _ = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="reabrir", lotes=[cubierto_id])

    assert response.status_code == 422
    assert bonita.acciones == []


def test_reformular_reemplaza_los_lotes_elegidos(client, session, auth_headers, bonita):
    emergencia_id, _, faltante_id = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="reformular", lotes=[faltante_id],
                       nuevosLotes=[{"tipoRecurso": "Personal", "descripcion": "Bomberos", "cantidad": 3}])

    assert response.status_code == 200
    assert bonita.acciones == [("GENERAR_LOTES", faltante_id)]
    assert bonita.completadas == ["10"]
    session.expire_all()
    assert session.get(Lote, faltante_id).estado == LoteEstado.REFORMULADO
    [nuevo] = response.json()
    assert nuevo["descripcion"] == "Bomberos"


def test_si_bonita_falla_al_liberar_se_informa_y_no_queda_la_decision(client, session, auth_headers, bonita):
    bonita.falla_liberacion = True
    emergencia_id, _, faltante_id = crear_emergencia(session)

    response = decidir(client, auth_headers, emergencia_id, accion="reformular", lotes=[faltante_id],
                       nuevosLotes=[{"tipoRecurso": "Personal", "descripcion": "Bomberos", "cantidad": 3}])

    assert response.status_code == 502
    assert "liberación de reservas" in response.json()["detail"]
    session.expire_all()
    assert session.get(Emergencia, emergencia_id).decisionesCoordinador == []
    assert session.get(Lote, faltante_id).estado == LoteEstado.CREADO


def test_bonita_libera_las_reservas_de_todos_los_lotes_elegidos(client, session, auth_headers, bonita):
    emergencia_id, cubierto_id, faltante_id = crear_emergencia(session)
    emergencia = session.get(Emergencia, emergencia_id)
    emergencia.decisionesCoordinador = [{"accion": "reabrir", "lotes": [cubierto_id, faltante_id]}]
    session.add(emergencia)
    session.commit()

    response = client.get(f"/api/rescue/integraciones/bonita/casos/1001/lotes/{faltante_id}/reservas",
                          headers=auth_headers("bonita_user"))

    assert response.status_code == 200
    assert len(response.json()["resultados"]) == 2
