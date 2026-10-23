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
from services.ejecucion import ongs_adjudicadas

TAREA_MONITOREO = "Monitorear la ejecucion"
TAREA_ONGS = "Ejecutar y finalizar actividades de ayuda"

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

        ongs = ongs_adjudicadas(session, emergencia.id)
        respuesta.append({
            "id": emergencia.id,
            "zona": emergencia.zonaAfectada,
            "lotes": lista_lotes,
            "ongs": [{"cuit": o["cuit"], "nombre": o["nombre"], "finalizado_en": o["finalizado_en"]} for o in ongs],
            "todas_finalizaron": all(o["finalizado_en"] for o in ongs),
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

    pendientes = [o["nombre"] for o in ongs_adjudicadas(session, emergencia_id) if not o["finalizado_en"]]
    if pendientes:
        raise HTTPException(
            status_code=409,
            detail=f"Todavía no terminaron su trabajo: {', '.join(pendientes)}."
        )

    tareas = {t["name"].strip(): t for t in await bonita.obtener_tareas_humanas_por_caso(emergencia.bonitaCaseId)}
    if TAREA_MONITOREO not in tareas and TAREA_ONGS not in tareas:
        raise HTTPException(status_code=409, detail="El caso todavía no está en la etapa de monitoreo.")

    try:
        # Si un intento anterior ya completó el monitoreo, se retoma desde la tarea de las ONGs.
        if TAREA_MONITOREO in tareas:
            await bonita.completar_tarea_humana(tareas[TAREA_MONITOREO]["id"])
            tareas = {t["name"].strip(): t for t in await bonita.esperar_tareas_humanas_por_caso(
                emergencia.bonitaCaseId, nombre_esperado=TAREA_ONGS
            )}
        # Las ONGs ya informaron el fin de su trabajo en la aplicación, así que su tarea del
        # proceso se completa acá; después Bonita cierra el caso.
        await bonita.completar_tarea_humana(tareas[TAREA_ONGS]["id"])
        emergencia.estado = EmergenciaEstado.MONITOREO_FINALIZADO
        session.add(emergencia)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
