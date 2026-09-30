import os
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Response
from dependencies.jwt_auth import get_current_user
from dependencies.bonita import get_bonita_service
from dependencies.rbac import (
    require_roles, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, AUDITORES, USUARIO_BONITA
)
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models.emergencia import Emergencia
from services.bonita_service import BonitaService
from typing import List
from models.lote import Lote
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel

PROCESS_NAME = os.getenv("BONITA_PROCESS")

router = APIRouter(
    prefix="/emergencias",
    tags=["emergencias"]
)
@router.get("", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, *AUDITORES))])
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

    return session.exec(query.order_by(Emergencia.fechaCreacion.desc(), Emergencia.id.desc())).all()

@router.get("/{emergencia_id}", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, *AUDITORES))])
def read_emergencia(
    emergencia_id: int,
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    return emergencia

@router.post("", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL))])
async def create_emergencia(
    emergencia: Emergencia,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    try:
        proceso = await bonita.obtener_proceso_por_nombre(PROCESS_NAME)
        if not proceso:
            raise Exception(f"No existe el proceso '{PROCESS_NAME}' en Bonita")

        iniciar_proceso_response = await bonita.iniciar_proceso(proceso["id"]) # devuelve un case id, setear a la emergencia

        emergencia.bonitaCaseId = iniciar_proceso_response["caseId"] # Asigna el case ID de Bonita a la emergencia
        
        session.add(emergencia) # Agrega la emergencia a la sesión de la base de datos
        
        # Espera hasta que aparezcan tareas humanas en estado 'ready' para el caso específico
        tarea_registrar_emergencia = await bonita.esperar_tarea_humana_por_caso(emergencia.bonitaCaseId)

        # Si es exitoso devuelve un HTTP 204, no devuelve nada, solo completa la tarea humana
        # La tarea "Registrar emergencia" define un contrato con emergenciaInput obligatorio
        await bonita.completar_tarea_humana(tarea_registrar_emergencia["id"], {
            "emergenciaInput": {
                "zonaAfectada": emergencia.zonaAfectada,
                "nivelGravedad": emergencia.nivelGravedad,
                "descripcionInicial": emergencia.descripcionInicial
            }
        })

        session.commit()
        session.refresh(emergencia) # Refresca la instancia de la emergencia desde la base de datos para obtener los valores actualizados
        
    except Exception as e:
        # Revertir los cambios en la sesión de la base de datos en caso de error
        session.rollback()
        
        # Borra el caso en Bonita si existe
        if emergencia.bonitaCaseId:
            await bonita.borrar_caso_por_id(emergencia.bonitaCaseId)

        raise HTTPException( 
            status_code=500,
            detail=str(e)
        )

    return emergencia

@router.delete("/{emergencia_id}", dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL))])
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


@router.get(
    "/{emergencia_id}/lotes",
    response_model=List[Lote],
    dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, *AUDITORES))]
)
def get_lotes_by_emergencia(
    emergencia_id: int,
    session: Session = Depends(get_session)
):

    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
    
    abiertos= select(Lote).where(
        Lote.emergenciaId == emergencia_id,
        Lote.estado == "abierto"
    )
    lotes = session.exec(abiertos.order_by(Lote.fechaCreacion.desc(), Lote.id.desc())).all()
    return lotes

class NotificarTimeoutRequest(BaseModel):
    case_id: str

# Endpoint para notificar el timeout de una emergencia en Bonita
# recibe json
@router.post("/notificar_timeout", dependencies=[Depends(require_roles(USUARIO_BONITA))], status_code=204)
async def notificar_por_timeout(
    request: NotificarTimeoutRequest,
    session: Session = Depends(get_session)
):  
    # buscar emergencia por case_id en Bonita
    emergencia = session.exec(select(Emergencia).where(Emergencia.bonitaCaseId == request.case_id)).first()
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")

    emergencia.estado = "convocatoria_cerrada"
    session.commit()

    return Response(status_code=204)
