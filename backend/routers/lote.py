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
from models.emergencia import Emergencia
from models.lote import Lote
PROCESS_NAME = os.getenv("BONITA_PROCESS")

router = APIRouter(
    prefix="/lotes",
    tags=["lotes"]
)

class LoteItemDTO(BaseModel):
    tipoRecurso: str
    descripcion: str
    cantidad: int

class DesgloseLotesRequest(BaseModel):
    emergenciaId: int
    lotes: list[LoteItemDTO]

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

    if emergencia.estado != "creada":
        raise HTTPException(
            status_code=400,
            detail="La emergencia no se encuentra en estado 'creada'."
        )

    if not payload.lotes:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un lote")

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
                cantidad=item.cantidad,
                cantidadCubierta=0,
                estado="creado",
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

        emergencia.estado = "publicada"
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
