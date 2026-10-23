"""Decisión del Centro Coordinador cuando la convocatoria cierra sin cobertura suficiente.

Se decide una vez por emergencia, evaluando todas sus ofertas en conjunto: Bonita tiene una
única tarea "Evaluar acciones a tomar" por caso, que recién aparece cuando venció la ventana
para ofertar y el Sistema Nacional validó las ofertas.
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from dependencies.bonita import get_bonita_service
from dependencies.jwt_auth import get_current_user
from dependencies.rbac import require_roles, CENTRO_COORDINADOR
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from routers.lote import LoteItemDTO, calcular_fecha_limite_demo, calcular_diferencia_ms
from services.bonita_service import BonitaService
from services.validacion_ofertas import reiniciar_validacion, resultado_guardado, utc

TAREA_EVALUAR = "Evaluar acciones a tomar"

router = APIRouter(
    prefix="/emergencias",
    tags=["decisión del coordinador"]
)


class DecisionRequest(BaseModel):
    accion: Literal["parcial", "reabrir", "reformular"]
    lotes: list[int] = []  # Lotes a reabrir o reformular, elegidos por el coordinador
    nuevosLotes: list[LoteItemDTO] = []  # Sólo para reformular


def lotes_vigentes(session: Session, emergencia_id: int) -> list[Lote]:
    return session.exec(select(Lote).where(
        Lote.emergenciaId == emergencia_id, Lote.estado != LoteEstado.REFORMULADO
    ).order_by(Lote.id)).all()


def convocatoria_terminada(lotes: list[Lote], ahora: datetime) -> bool:
    return bool(lotes) and all(utc(lote.fechaLimiteConvocatoria) < ahora for lote in lotes)


async def espera_decision(bonita: BonitaService, emergencia: Emergencia) -> bool:
    tareas = await bonita.obtener_tareas_humanas_por_caso(emergencia.bonitaCaseId)
    return any(tarea["name"].strip() == TAREA_EVALUAR for tarea in tareas)


def armar_evaluacion(session: Session, emergencia: Emergencia, lotes: list[Lote]) -> dict:
    cobertura = {c["lote_id"]: c for c in resultado_guardado(session, emergencia.id)["cobertura_por_lote"]}
    respuesta_lotes = []
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote.id).order_by(Oferta.id)).all()
        respuesta_ofertas = []
        for oferta in ofertas:
            participantes = session.exec(select(ParticipanteOferta).where(
                ParticipanteOferta.oferta_id == oferta.id, ParticipanteOferta.cantidad_aportada != None
            )).all()
            respuesta_ofertas.append({
                "id": oferta.id,
                "ong_lider_id": oferta.ong_lider_id,
                "valida": oferta.valida,
                "estado_validacion": oferta.estado_validacion,
                "cantidad_ofertada": sum(p.cantidad_aportada for p in participantes),
                "resultado_validacion": oferta.resultado_validacion,
                "validada_en": oferta.validada_en,
            })
        cobertura_lote = cobertura.get(lote.id, {})
        respuesta_lotes.append({
            "id": lote.id,
            "tipoRecurso": lote.tipoRecurso,
            "descripcion": lote.descripcion,
            "cantidad": lote.cantidad,
            "fechaLimiteConvocatoria": lote.fechaLimiteConvocatoria,
            "cantidad_ofertada": cobertura_lote.get("cantidad_ofertada", 0),
            "ofertado_valido": cobertura_lote.get("ofertado_valido", 0),
            "faltante": cobertura_lote.get("faltante", lote.cantidad),
            "cubierto": cobertura_lote.get("cubierto", False),
            "ofertas": respuesta_ofertas,
        })
    return {
        "id": emergencia.id,
        "zonaAfectada": emergencia.zonaAfectada,
        "nivelGravedad": emergencia.nivelGravedad,
        "descripcionInicial": emergencia.descripcionInicial,
        "decisionesCoordinador": emergencia.decisionesCoordinador,
        "lotes": respuesta_lotes,
    }


def registrar_decision(emergencia: Emergencia, accion: str, lotes_ids: list[int], usuario: str | None):
    decision = {
        "accion": accion,
        "lotes": lotes_ids,
        "usuario": usuario,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    # Se reasigna la lista para que SQLAlchemy detecte el cambio en la columna JSON.
    emergencia.decisionesCoordinador = [*(emergencia.decisionesCoordinador or []), decision]


@router.get(
    "/pendientes-decision",
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def get_emergencias_pendientes_decision(
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    ahora = datetime.now(timezone.utc)
    emergencias = session.exec(select(Emergencia).where(
        Emergencia.estado.in_([EmergenciaEstado.PUBLICADA, EmergenciaEstado.CONVOCATORIA_CERRADA]),
        Emergencia.bonitaCaseId != None
    ).order_by(Emergencia.fechaCreacion.desc(), Emergencia.id.desc())).all()

    resultado = []
    for emergencia in emergencias:
        lotes = lotes_vigentes(session, emergencia.id)
        # Mientras quede tiempo para ofertar no se evalúa: otra oferta puede completar la cobertura.
        if not convocatoria_terminada(lotes, ahora):
            continue
        if await espera_decision(bonita, emergencia):
            resultado.append(armar_evaluacion(session, emergencia, lotes))
    return resultado


@router.post(
    "/{emergencia_id}/decision",
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def decidir_emergencia(
    emergencia_id: int,
    data: DecisionRequest,
    current_user: dict = Depends(get_current_user),
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    if not emergencia.bonitaCaseId:
        raise HTTPException(status_code=409, detail="Esta emergencia no tiene un caso asociado en Bonita.")

    ahora = datetime.now(timezone.utc)
    lotes = lotes_vigentes(session, emergencia.id)
    if not convocatoria_terminada(lotes, ahora):
        raise HTTPException(
            status_code=409,
            detail="La convocatoria todavía está abierta. Hay que esperar a que termine el tiempo para ofertar."
        )
    if not await espera_decision(bonita, emergencia):
        raise HTTPException(
            status_code=409,
            detail="La emergencia no está esperando una decisión del coordinador: las ofertas se están validando o ya se decidió."
        )

    usuario = current_user.get("sub")
    if data.accion == "parcial":
        return await aceptar_cobertura_parcial(session, bonita, emergencia, lotes, usuario)

    cobertura = {c["lote_id"]: c for c in resultado_guardado(session, emergencia.id)["cobertura_por_lote"]}
    lotes_por_id = {lote.id: lote for lote in lotes}
    elegidos = sorted(set(data.lotes))
    if not elegidos:
        raise HTTPException(status_code=422, detail="Elegí al menos un lote.")
    if any(lote_id not in lotes_por_id for lote_id in elegidos):
        raise HTTPException(status_code=422, detail="Alguno de los lotes elegidos no pertenece a la emergencia.")
    if any(cobertura.get(lote_id, {}).get("cubierto") for lote_id in elegidos):
        raise HTTPException(status_code=422, detail="Sólo se pueden elegir lotes que no alcanzaron la cantidad necesaria.")
    if data.accion == "reformular" and not data.nuevosLotes:
        raise HTTPException(status_code=422, detail="Debe incluir al menos un lote nuevo.")

    seleccionados = [lotes_por_id[lote_id] for lote_id in elegidos]
    registrar_decision(emergencia, data.accion, elegidos, usuario)
    session.add(emergencia)
    # Bonita libera en el Sistema Nacional las reservas de los lotes elegidos al completar la tarea:
    # consulta /lotes/{id}/reservas, que lee esta decisión, así que tiene que estar guardada antes.
    session.commit()

    if data.accion == "reabrir":
        return await reabrir_convocatoria(session, bonita, emergencia, seleccionados, ahora)
    return await reformular_lotes(session, bonita, emergencia, seleccionados, data.nuevosLotes, ahora)


async def aceptar_cobertura_parcial(session, bonita, emergencia, lotes, usuario):
    ofertas = session.exec(select(Oferta).where(Oferta.lote_id.in_([lote.id for lote in lotes]))).all()
    if any(oferta.estado_validacion == "pendiente" for oferta in ofertas):
        raise HTTPException(status_code=409, detail="Primero debe completarse la consulta de recursos de todas las ofertas.")

    hay_recursos = any(oferta.valida for oferta in ofertas)
    for oferta in ofertas:
        resultado = oferta.resultado_validacion
        if oferta.valida or not resultado or resultado.get("cantidad_verificada", 0) <= 0:
            continue
        # Conservar lo prometido y aceptar sólo la cantidad respaldada por inventario.
        resultado = dict(resultado)
        resultado["cantidad_aceptada"] = resultado["cantidad_verificada"]
        resultado["participantes"] = [{**p, "cantidad_aceptada": p["cantidad_verificada"]}
                                      for p in resultado.get("participantes", [])]
        oferta.resultado_validacion = resultado
        session.add(oferta)
        hay_recursos = True

    if not hay_recursos:
        raise HTTPException(
            status_code=400,
            detail="Ninguna oferta tiene recursos disponibles: no se puede continuar con cobertura parcial."
        )

    registrar_decision(emergencia, "parcial", [], usuario)
    session.add(emergencia)
    try:
        await bonita.resolver_accion_coordinador(emergencia.bonitaCaseId, "ACEPTAR_OFERTAS")
    except Exception:
        session.rollback()
        raise
    session.commit()
    return {"mensaje": "Se continúa con cobertura parcial."}


def deshacer_decision(session: Session, emergencia: Emergencia):
    session.rollback()
    session.refresh(emergencia)
    emergencia.decisionesCoordinador = emergencia.decisionesCoordinador[:-1]
    session.add(emergencia)
    session.commit()


async def esperar_siguiente_tarea(session, bonita, emergencia, nombre, timeout_segundos=20):
    """Esperar la tarea a la que avanza el caso tras la decisión.

    Bonita ejecuta la liberación de reservas después de aceptar la tarea, así que un fallo ahí
    no vuelve en la llamada: la tarea queda en estado 'failed' y el caso no avanza.
    """
    inicio = time.monotonic()
    while True:
        tareas = await bonita.obtener_tareas_humanas_por_caso(emergencia.bonitaCaseId)
        tarea = next((t for t in tareas if t["name"].strip() == nombre.strip()), None)
        if tarea:
            return tarea
        if await bonita.obtener_tareas_humanas_fallidas_por_caso(emergencia.bonitaCaseId):
            deshacer_decision(session, emergencia)
            raise HTTPException(
                status_code=502,
                detail="Bonita no pudo aplicar la decisión: falló la liberación de reservas en el Sistema Nacional "
                       "y el caso quedó detenido. Revisá los logs de bonita-engine."
            )
        if time.monotonic() - inicio >= timeout_segundos:
            raise HTTPException(status_code=504, detail=f"Bonita no llegó a la tarea '{nombre.strip()}' a tiempo.")
        await asyncio.sleep(0.2)


async def reabrir_convocatoria(session, bonita, emergencia, seleccionados, ahora):
    caso_id = emergencia.bonitaCaseId
    fecha_limite = calcular_fecha_limite_demo(emergencia.nivelGravedad, ahora)
    try:
        await bonita.set_case_variable(
            caso_id, "ventana_tiempo_ms", "java.lang.Long", calcular_diferencia_ms(fecha_limite, ahora)
        )
        # Bonita recibe un solo lote; /lotes/{id}/reservas devuelve las reservas de todos los elegidos.
        await bonita.resolver_accion_coordinador(caso_id, "PUBLICAR_CONVOCATORIA", seleccionados[0].id)
    except Exception as e:
        deshacer_decision(session, emergencia)
        raise error_http(e) from e

    try:
        await esperar_siguiente_tarea(session, bonita, emergencia, "Cargar ofertas de  ayuda")
        for lote in seleccionados:
            reiniciar_validacion(session, lote.id)
            lote.fechaLimiteConvocatoria = fecha_limite
            session.add(lote)
        emergencia.estado = EmergenciaEstado.PUBLICADA
        session.add(emergencia)
        session.commit()
    except Exception as e:
        session.rollback()
        raise error_http(e) from e
    return {"mensaje": "Convocatoria reabierta correctamente."}


async def reformular_lotes(session, bonita, emergencia, seleccionados, nuevos_lotes, ahora):
    caso_id = emergencia.bonitaCaseId
    fecha_limite = calcular_fecha_limite_demo(emergencia.nivelGravedad, ahora)
    try:
        await bonita.set_case_variable(
            caso_id, "ventana_tiempo_ms", "java.lang.Long", calcular_diferencia_ms(fecha_limite, ahora)
        )
        # Bonita recibe un solo lote; /lotes/{id}/reservas devuelve las reservas de todos los elegidos.
        await bonita.resolver_accion_coordinador(caso_id, "GENERAR_LOTES", seleccionados[0].id)
    except Exception as e:
        deshacer_decision(session, emergencia)
        raise error_http(e) from e

    try:
        tarea_generacion = await esperar_siguiente_tarea(session, bonita, emergencia, "Generar lotes de necesidades")
        for lote in seleccionados:
            reiniciar_validacion(session, lote.id)
            lote.estado = LoteEstado.REFORMULADO
            session.add(lote)
        lotes_creados = [Lote(
            emergenciaId=emergencia.id,
            tipoRecurso=item.tipoRecurso,
            descripcion=item.descripcion,
            recurso_codigo=item.recurso_codigo,
            cantidad=item.cantidad,
            cantidadCubierta=0,
            estado=LoteEstado.CREADO,
            fechaLimiteConvocatoria=fecha_limite,
            loteOrigenId=seleccionados[0].id if len(seleccionados) == 1 else None
        ) for item in nuevos_lotes]
        session.add_all(lotes_creados)
        # Los nuevos lotes ya se cargaron en esta misma solicitud.
        await bonita.completar_tarea_humana(tarea_generacion["id"])
        emergencia.estado = EmergenciaEstado.PUBLICADA
        session.add(emergencia)
        session.commit()
    except Exception as e:
        session.rollback()
        raise error_http(e) from e

    for lote in lotes_creados:
        session.refresh(lote)
    return lotes_creados


def error_http(error: Exception) -> HTTPException:
    return error if isinstance(error, HTTPException) else HTTPException(status_code=500, detail=str(error))
