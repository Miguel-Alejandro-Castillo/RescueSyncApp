from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from dependencies.bonita import get_bonita_service
from dependencies.jwt_auth import get_current_user
from dependencies.rbac import require_roles, CENTRO_COORDINADOR
from models.emergencia import Emergencia, EmergenciaEstado
from models.evento_ejecucion import EventoEjecucion
from models.lote import Lote, LoteEstado
from services.bonita_service import BonitaService

router = APIRouter(
    prefix="/monitoreo",
    tags=["monitoreo"],
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)

class EventoRequest(BaseModel):
    descripcion: str

@router.get("")
def get_monitoreo(session: Session = Depends(get_session)):
    emergencias = session.exec(
        select(Emergencia).where(Emergencia.estado != EmergenciaEstado.MONITOREO_FINALIZADO)
    ).all()

    respuesta = []
    for emergencia in emergencias:
        lotes = session.exec(
            select(Lote).where(
                Lote.emergenciaId == emergencia.id,
                Lote.estado == LoteEstado.ADJUDICADO
            )
        ).all()
        if not lotes:
            continue

        lista_lotes = []
        for lote in lotes:
            eventos = session.exec(
                select(EventoEjecucion)
                .where(EventoEjecucion.lote_id == lote.id)
                .order_by(EventoEjecucion.fecha.desc())
            ).all()
            lista_lotes.append({
                "id": lote.id,
                "tipo": lote.tipoRecurso,
                "descripcion": lote.descripcion,
                "cantidad": lote.cantidad,
                "eventos": [
                    {"id": e.id, "descripcion": e.descripcion, "fecha": e.fecha.isoformat()}
                    for e in eventos
                ]
            })

        respuesta.append({
            "id": emergencia.id,
            "zona": emergencia.zonaAfectada,
            "lotes": lista_lotes
        })

    return respuesta

@router.post("/lotes/{lote_id}/eventos", status_code=status.HTTP_201_CREATED)
def registrar_evento(
    lote_id: int,
    data: EventoRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")

    if lote.estado != LoteEstado.ADJUDICADO:
        raise HTTPException(status_code=400, detail="El lote todavía no fue adjudicado.")

    descripcion = data.descripcion.strip()
    if not descripcion:
        raise HTTPException(status_code=422, detail="Ingrese la descripción del evento.")
    if len(descripcion) > 500:
        raise HTTPException(status_code=422, detail="La descripción no puede superar los 500 caracteres.")

    evento = EventoEjecucion(
        lote_id=lote_id,
        usuario_id=str(current_user["user_id"]),
        descripcion=descripcion
    )
    session.add(evento)
    session.commit()
    session.refresh(evento)

    return evento

@router.post("/emergencias/{emergencia_id}/finalizar", status_code=status.HTTP_204_NO_CONTENT)
async def finalizar_monitoreo(
    emergencia_id: int,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="La emergencia no existe.")

    if not emergencia.bonitaCaseId:
        raise HTTPException(status_code=409, detail="Esta emergencia no tiene un caso asociado en Bonita.")

    tareas = await bonita.obtener_tareas_humanas_por_caso(emergencia.bonitaCaseId)
    tarea = next((t for t in tareas if t["name"].strip() == "Monitorear la ejecucion"), None)
    if not tarea:
        raise HTTPException(status_code=409, detail="El caso todavía no está en la etapa de monitoreo.")

    try:
        await bonita.completar_tarea_humana(tarea["id"])
        emergencia.estado = EmergenciaEstado.MONITOREO_FINALIZADO
        session.add(emergencia)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
