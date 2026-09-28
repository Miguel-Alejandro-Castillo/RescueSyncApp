from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from database import get_session
from models.emergencia import Emergencia
from models.lote import Lote
from models.oferta import Oferta

router = APIRouter(
    prefix="/ofertas",
    tags=["ofertas"]
)


TIEMPO_LIMITE_GRAVEDAD = {
    "Critica": timedelta(hours=24),
    "Alta": timedelta(hours=72),
    "Medio": timedelta(hours=168)
}

def es_lote_vigente(lote: Lote, emergencia: Emergencia) -> bool:

    duracion_permitida = TIEMPO_LIMITE_GRAVEDAD.get(
        emergencia.nivelGravedad, 
        timedelta(hours=48)  
    )
    
    fecha_expiracion = lote.fecha_publicacion + duracion_permitida
    ahora = datetime.now(timezone.utc)
 
    if lote.fecha_publicacion.tzinfo is None:
        ahora = datetime.now()

    return ahora <= fecha_expiracion

@router.get("/emergencias-disponibles")
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


@router.post("/", status_code=status.HTTP_201_CREATED)
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
    emergencia = session.get(Emergencia, lote.id_emergencia)
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
    cant_cubierta_actual = lote.cant_cubierta or 0
    faltante = lote.cantidad - cant_cubierta_actual
    if oferta.cant_recurso > faltante:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La oferta supera lo requerido. Solo faltan {faltante} unidades para completar el lote."
        )

    session.add(oferta)
    lote.cant_cubierta += oferta.cant_recurso
    if lote.cant_cubierta == lote.cantidad:

        lote.estado = "cubierto"

    print(lote.cant_cubierta)    
    session.add(lote)

    session.commit()

    session.refresh(oferta)
    session.refresh(lote)
    return oferta