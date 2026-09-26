import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models.emergencia import Emergencia
from services.bonita_service import BonitaService

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
    session: Session = Depends(get_session)
):
    session.add(emergencia)
    session.commit()
    session.refresh(emergencia)

    bonita = BonitaService()
    try:
        await bonita.login(os.getenv("BONITA_USER"), os.getenv("BONITA_PASSWORD"))
        procesos = await bonita.obtener_procesos_por_nombre(os.getenv("BONITA_PROCESS"))
        await bonita.iniciar_proceso(procesos[0]["id"])
    except Exception:
        session.delete(emergencia)
        session.commit()
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