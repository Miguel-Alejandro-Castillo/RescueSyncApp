from services.validacion_ofertas import reiniciar_validacion
import os
from datetime import datetime, timedelta, timezone
from dependencies.bonita import get_bonita_service
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from dependencies.rbac import (
    require_roles, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, AUDITORES
)
from services.bonita_service import BonitaService
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta

router = APIRouter(
    prefix="/lotes",
    tags=["lotes"]
)

class LoteItemDTO(BaseModel):
    tipoRecurso: str
    descripcion: str
    cantidad: int
    recurso_codigo: str | None = None

class DesgloseLotesRequest(BaseModel):
    emergenciaId: int
    lotes: list[LoteItemDTO]

class ReformularLotesRequest(BaseModel):
    ofertaId: int
    lotes: list[LoteItemDTO]

class ReabrirConvocatoriaRequest(BaseModel):
    ofertaId: int
    

class ParticipanteOfertaResponse(BaseModel):
    id: int
    ong_id: int
    ong_name: str
    cantidad_aportada: int | None = None

class OfertaLoteResponse(BaseModel):
    id: int
    tipo_oferta: str
    participantes: list[ParticipanteOfertaResponse]

def calcular_fecha_limite(nivel_gravedad: str, fecha_inicio: datetime) -> datetime:
    horas_map = {
        "critico": 24,
        "alto": 48,
        "medio": 72,
        "bajo": 96
    }
    horas = horas_map.get(nivel_gravedad.lower(), 96)
    return fecha_inicio + timedelta(hours=horas)

def calcular_fecha_limite_demo(nivel_gravedad: str, fecha_inicio: datetime) -> datetime:
    minutos_map = {
        "critico": 2,
        "alto": 4,
        "medio": 6,
        "bajo": 8
    }

    minutos = minutos_map.get(nivel_gravedad.lower(), 8)
    return fecha_inicio + timedelta(minutes=minutos)

def calcular_diferencia_ms(fecha_limite: datetime, fecha_actual: datetime) -> int:
    diferencia = fecha_limite - fecha_actual
    return int(diferencia.total_seconds() * 1000)

@router.get("", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, *AUDITORES))])
def read_lotes(
    emergenciaId: int | None = None,
    estado: str | None = None,
    tipoRecurso: str | None = None,
    session: Session = Depends(get_session)
):
    query = select(Lote)

    if emergenciaId:
        query = query.where(Lote.emergenciaId == emergenciaId)
    if estado:
        query = query.where(Lote.estado == estado)
    if tipoRecurso:
        query = query.where(Lote.tipoRecurso == tipoRecurso)

    return session.exec(query.order_by(Lote.fechaCreacion.desc(), Lote.id.desc())).all()

@router.get("/{lote_id}", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, *AUDITORES))])
def read_lote(
    lote_id: int,
    session: Session = Depends(get_session)
):
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def create_lotes(
    payload: DesgloseLotesRequest,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, payload.emergenciaId)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")

    if emergencia.estado != EmergenciaEstado.CREADA:
        raise HTTPException(
            status_code=400,
            detail=f"La emergencia no se encuentra en estado '{EmergenciaEstado.CREADA}'."
        )

    if not payload.lotes:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un lote")

    if not emergencia.bonitaCaseId:
        raise HTTPException(
            status_code=409,
            detail="Esta emergencia no tiene un caso asociado en Bonita. Registrá una nueva emergencia desde la aplicación para poder publicar lotes."
        )

    ahora = datetime.now(timezone.utc)
    fecha_limite = calcular_fecha_limite_demo(emergencia.nivelGravedad, ahora)
    ventana_emergencia_ms = calcular_diferencia_ms(fecha_limite, ahora)

    try:
        lotes_creados = []
        for item in payload.lotes:
            nuevo_lote = Lote(
                emergenciaId=payload.emergenciaId,
                tipoRecurso=item.tipoRecurso,
                descripcion=item.descripcion,
                recurso_codigo=item.recurso_codigo,
                cantidad=item.cantidad,
                cantidadCubierta=0,
                estado=LoteEstado.CREADO,
                fechaLimiteConvocatoria=fecha_limite
            )
            session.add(nuevo_lote)
            lotes_creados.append(nuevo_lote)

        caso_id = emergencia.bonitaCaseId

        # 1. Setear ventana de tiempo
        await bonita.set_case_variable(
            caso_id,
            "ventana_tiempo_ms",
            "java.lang.Long",
            ventana_emergencia_ms
        )

        # 2. Obtener tarea humana pendiente
        tareas = await bonita.obtener_tareas_humanas_por_caso(caso_id)

        if not tareas:
            raise Exception(
                "No se encontró una tarea humana pendiente para la emergencia"
            )

        # 3. Buscar específicamente Generar lotes de necesidades
        tarea = next(
            (
                tarea for tarea in tareas
                if tarea["name"] == "Generar lotes de necesidades"
            ),
            None
        )

        if not tarea:
            raise Exception(
                "No se encontró la tarea 'Generar lotes de necesidades'"
            )

        # 4. Completar tarea
        await bonita.completar_tarea_humana(tarea["id"])    

        emergencia.estado = EmergenciaEstado.PUBLICADA
        session.add(emergencia)

        session.commit()

        for lote in lotes_creados:
            session.refresh(lote)
    except Exception as e:
        session.rollback()
        
        raise HTTPException( 
                    status_code=500,
                    detail=str(e)
        )
    return lotes_creados

@router.post(
    "/reformular",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def reformular_lotes(
    payload: ReformularLotesRequest,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    oferta = session.get(Oferta, payload.ofertaId)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    if oferta.valida or oferta.accion_tomada != "reformular":
        raise HTTPException(
            status_code=400,
            detail="La oferta no tiene confirmada la acción de reformular lotes."
        )

    lote_anterior = session.get(Lote, oferta.lote_id)
    if lote_anterior.estado == LoteEstado.REFORMULADO:
        raise HTTPException(status_code=400, detail="Los lotes de esta oferta ya fueron reformulados.")

    if not payload.lotes:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un lote")

    emergencia = session.get(Emergencia, lote_anterior.emergenciaId)
    if not emergencia.bonitaCaseId:
        raise HTTPException(
            status_code=409,
            detail="Esta emergencia no tiene un caso asociado en Bonita."
        )

    ahora = datetime.now(timezone.utc)
    fecha_limite = calcular_fecha_limite_demo(emergencia.nivelGravedad, ahora)
    ventana_emergencia_ms = calcular_diferencia_ms(fecha_limite, ahora)

    try:
        lote_anterior.estado = LoteEstado.REFORMULADO
        session.add(lote_anterior)

        lotes_creados = []
        for item in payload.lotes:
            nuevo_lote = Lote(
                emergenciaId=emergencia.id,
                tipoRecurso=item.tipoRecurso,
                descripcion=item.descripcion,
                recurso_codigo=item.recurso_codigo,
                cantidad=item.cantidad,
                cantidadCubierta=0,
                estado=LoteEstado.CREADO,
                fechaLimiteConvocatoria=fecha_limite,
                loteOrigenId=lote_anterior.id
            )
            session.add(nuevo_lote)
            lotes_creados.append(nuevo_lote)

        caso_id = emergencia.bonitaCaseId

        await bonita.set_case_variable(
            caso_id,
            "ventana_tiempo_ms",
            "java.lang.Long",
            ventana_emergencia_ms
        )

        await bonita.resolver_accion_coordinador(caso_id, "GENERAR_LOTES", lote_anterior.id)
        # Los nuevos lotes ya se cargaron en esta misma solicitud.
        tareas_generacion = await bonita.esperar_tareas_humanas_por_caso(caso_id, nombre_esperado="Generar lotes de necesidades")
        tarea_generacion = next((t for t in tareas_generacion
                                 if t["name"].strip() == "Generar lotes de necesidades"), None)
        if not tarea_generacion:
            raise HTTPException(409, "Bonita no llegó a la tarea de generar los nuevos lotes.")
        reiniciar_validacion(session, lote_anterior.id)
        await bonita.completar_tarea_humana(tarea_generacion["id"])
        emergencia.estado = "publicada"
        session.add(emergencia)

        session.commit()

        for lote in lotes_creados:
            session.refresh(lote)
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    return lotes_creados

@router.post(
    "/reabrir",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def reabrir_convocatoria(
    payload: ReabrirConvocatoriaRequest,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    oferta = session.get(Oferta, payload.ofertaId)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    if oferta.valida or oferta.accion_tomada != "reabrir":
        raise HTTPException(
            status_code=400,
            detail="La oferta no tiene confirmada la acción de reabrir la convocatoria."
        )

    lote_oferta = session.get(Lote, oferta.lote_id)
    emergencia = session.get(Emergencia, lote_oferta.emergenciaId)
    if not emergencia.bonitaCaseId:
        raise HTTPException(
            status_code=409,
            detail="Esta emergencia no tiene un caso asociado en Bonita."
        )

    ahora = datetime.now(timezone.utc)
    fecha_limite = calcular_fecha_limite_demo(emergencia.nivelGravedad, ahora)
    ventana_emergencia_ms = calcular_diferencia_ms(fecha_limite, ahora)

    try:
        lote_oferta.fechaLimiteConvocatoria = fecha_limite
        session.add(lote_oferta)

        emergencia.estado = EmergenciaEstado.PUBLICADA
        session.add(emergencia)

        caso_id = emergencia.bonitaCaseId

        await bonita.set_case_variable(
            caso_id,
            "ventana_tiempo_ms",
            "java.lang.Long",
            ventana_emergencia_ms
        )

        await bonita.resolver_accion_coordinador(caso_id, "PUBLICAR_CONVOCATORIA", lote_oferta.id)
        await bonita.esperar_tareas_humanas_por_caso(caso_id, nombre_esperado="Cargar ofertas de  ayuda")
        reiniciar_validacion(session, lote_oferta.id)

        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    return {"mensaje": "Convocatoria reabierta correctamente."}

@router.delete("/{lote_id}", dependencies=[Depends(require_roles(CENTRO_COORDINADOR))])
def delete_lote(
    lote_id: int,
    session: Session = Depends(get_session)
):
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    session.delete(lote)
    session.commit()
    return {"ok": True}

@router.get(
    "/{lote_id}/ofertas",
    response_model=list[OfertaLoteResponse],
    dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL))]
)
def get_ofertas_lote(
    lote_id: int,
    session: Session = Depends(get_session)
) -> list[OfertaLoteResponse]:
    lote = session.get(Lote, lote_id)

    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    ofertas = session.exec(
        select(Oferta).where(Oferta.lote_id == lote_id)
    ).all()

    ofertas_response = []
    for oferta in ofertas:
        participantes = session.exec(
            select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id, ParticipanteOferta.cantidad_aportada != None)
        ).all()
        tipo_oferta = "CONSORCIO" if len(participantes) > 1 else "INDIVIDUAL"

        oferta_response = OfertaLoteResponse(
            id=oferta.id,
            tipo_oferta=tipo_oferta,
            participantes=[ParticipanteOfertaResponse(
                id=participante.id,
                ong_id=participante.ong_id,
                ong_name="ONG " + str(participante.ong_id),
                cantidad_aportada=participante.cantidad_aportada
            ) for participante in participantes]
        )
        ofertas_response.append(oferta_response)

    return ofertas_response