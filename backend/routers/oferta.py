from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from database import get_session
from dependencies.rbac import (
    require_roles, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, AUDITORES
)
from models.emergencia import Emergencia
from models.lote import Lote
from models.oferta import Oferta

router = APIRouter(
    prefix="/ofertas",
    tags=["ofertas"]
)


def es_lote_vigente(lote: Lote, emergencia: Emergencia) -> bool:
    fecha_limite = lote.fechaLimiteConvocatoria
    if fecha_limite.tzinfo is None:
        fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) <= fecha_limite

@router.get(
    "/emergencias-disponibles",
    dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, *AUDITORES))]
)
def get_emergencias_con_lotes(
    session: Session = Depends(get_session)
):

    statement = select(Emergencia).where(Emergencia.estado == "publicada")
    emergencias = session.exec(statement).all()
    
    resultado = []
    for emergencia in emergencias:
       
        stmt_lotes = select(Lote).where(Lote.emergenciaId == emergencia.id)
        lotes = session.exec(stmt_lotes).all()

        
        resultado.append({
            "emergencia": emergencia,
            "lotes": lotes
        })
        
    return resultado


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def create_oferta(
    oferta: Oferta,
    session: Session = Depends(get_session)
):

    lote = session.get(Lote, oferta.id_lote)
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El lote con ID {oferta.id_lote} no existe."
        )
    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not emergencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La emergencia asociada al lote no existe."
        )

    #validar tiempo
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El plazo para realizar ofertas en este lote ha expirado. (Nivel de gravedad: {emergencia.nivelGravedad})"
        )
    cant_cubierta_actual = lote.cantidadCubierta or 0
    faltante = lote.cantidad - cant_cubierta_actual
    if oferta.cant_recurso > faltante:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La oferta supera lo requerido. Solo faltan {faltante} unidades para completar el lote."
        )

    session.add(oferta)
    lote.cantidadCubierta += oferta.cant_recurso
    if lote.cantidadCubierta == lote.cantidad:

        lote.estado = "cubierto"

    print(lote.cantidadCubierta)    
    session.add(lote)

    session.commit()

    session.refresh(oferta)
    session.refresh(lote)
    return oferta