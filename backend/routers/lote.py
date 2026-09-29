from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from dependencies.rbac import (
    require_roles, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, AUDITORES
)
from models.emergencia import Emergencia
from models.lote import Lote

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

def calcular_fecha_limite(nivel_gravedad: str) -> datetime:
    horas_map = {
        "critico": 24,
        "alto": 48,
        "medio": 72,
        "bajo": 96
    }
    horas = horas_map.get(nivel_gravedad.lower(), 96)
    return datetime.now(timezone.utc) + timedelta(hours=horas)

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

    return session.exec(query).all()

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
def create_lotes(
    payload: DesgloseLotesRequest,
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

    fecha_limite = calcular_fecha_limite(emergencia.nivelGravedad)

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

    emergencia.estado = "publicada"
    session.add(emergencia)

    session.commit()

    for lote in lotes_creados:
        session.refresh(lote)

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