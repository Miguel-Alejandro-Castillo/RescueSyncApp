import os
from datetime import datetime, timezone
from auth.jwt_auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models.emergencia import Emergencia
from services.bonita_service import BonitaService

PROCESS_NAME = os.getenv("BONITA_PROCESS")

router = APIRouter(
    prefix="/emergencias",
    tags=["emergencias"]
)
@router.get("")
def read_emergencias(
    estado: str | None = None,
    nivelGravedad: str | None = None,
    zonaAfectada: str | None = None,
    fechaDesde: datetime | None = None,
    fechaHasta: datetime | None = None,
    session: Session = Depends(get_session)
):
    query = select(Emergencia)

    if estado:
        query = query.where(Emergencia.estado == estado)
    if nivelGravedad:
        query = query.where(Emergencia.nivelGravedad == nivelGravedad)
    if zonaAfectada:
        query = query.where(Emergencia.zonaAfectada == zonaAfectada)
    if fechaDesde:
        if fechaDesde.tzinfo is None:
            fechaDesde = fechaDesde.replace(tzinfo=timezone.utc)
        query = query.where(Emergencia.fechaCreacion >= fechaDesde)
    if fechaHasta:
        if fechaHasta.tzinfo is None:
            fechaHasta = fechaHasta.replace(tzinfo=timezone.utc)
        query = query.where(Emergencia.fechaCreacion <= fechaHasta)

    return session.exec(query).all()

@router.get("/{emergencia_id}")
def read_emergencia(
    emergencia_id: int,
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    return emergencia

@router.post("")
async def create_emergencia(
    emergencia: Emergencia,
    current_user= Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # deberia extraer el token del usuario actual y usarlo en Bonita
    bonita = BonitaService()
    bonita.j_session = current_user["bonita_auth"]
    bonita.api_token = current_user["bonita_token"]
    
    session.add(emergencia)
    try:
        procesos = await bonita.obtener_procesos_por_nombre(PROCESS_NAME)
        processId = procesos[0]["id"]
        iniciar_proceso_response = await bonita.iniciar_proceso(processId) # devuelve un case id, setear a la emergencia

        emergencia.bonitaCaseId = iniciar_proceso_response["caseId"] # Asigna el case ID de Bonita a la emergencia
        
        # Espera hasta que aparezcan tareas humanas en estado 'ready' para el caso específico
        tareas_humanas = await bonita.esperar_tareas_humanas_por_caso(emergencia.bonitaCaseId)
        tarea_registrar_emergencia = tareas_humanas[0]

        # Si es exitoso devuelve un HTTP 204, no devuelve nada, solo completa la tarea humana
        await bonita.completar_tarea_humana(tarea_registrar_emergencia["id"])

        session.commit()
        session.refresh(emergencia)
        
    except Exception:
        session.rollback() # Revertir los cambios en la sesión de la base de datos en caso de error
        raise HTTPException(status_code=500, detail="No se pudo iniciar el proceso en Bonita")
    finally:
        await bonita.http_client.close()

    return emergencia

@router.delete("/{emergencia_id}")
def delete_emergencia(
    emergencia_id: int,
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    session.delete(emergencia)
    session.commit()
    return {"ok": True}