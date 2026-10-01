from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from database import get_session
from pydantic import BaseModel
from dependencies.rbac import (
    require_roles, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, AUDITORES
)
from models.emergencia import Emergencia
from models.lote import Lote
from models.oferta import Oferta
from dependencies.jwt_auth import get_current_user
from dependencies.rbac import get_user_roles



class OfertaUpdate(BaseModel):
    cant_recurso: int
    id_ong: int

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
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):

    statement = select(Emergencia).where(Emergencia.estado == "publicada").order_by(
        Emergencia.fechaCreacion.desc(), Emergencia.id.desc()
    )
    emergencias = session.exec(statement).all()
    
    resultado = []
    for emergencia in emergencias:
       
        stmt_lotes = select(Lote).where(Lote.emergenciaId == emergencia.id).order_by(
            Lote.fechaCreacion.desc(), Lote.id.desc()
        )
        if REPRESENTANTE_ONG in get_user_roles(current_user):
            ofertados = select(Oferta.id_lote).where(Oferta.id_ong == int(current_user['user_id']))
            stmt_lotes = stmt_lotes.where(Lote.estado.in_(['creado', 'activo', 'abierto']), Lote.id.not_in(ofertados))
        lotes = session.exec(stmt_lotes).all()
        if REPRESENTANTE_ONG in get_user_roles(current_user) and not lotes:
            continue

        
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
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):

    oferta.id_ong = int(current_user['user_id'])
    # SQLModel no valida los modelos con table=True, por eso se controla a mano
    if oferta.cant_recurso <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cantidad ofrecida debe ser mayor a 0."
        )

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
            detail="La convocatoria de este lote ha expirado. Ya no podés enviar una oferta."
        )
   #Evitar que la misma ONG oferte más de una vez para el mismo lote
    stmt_existente = select(Oferta).where(
        Oferta.id_lote == oferta.id_lote,
        Oferta.id_ong == oferta.id_ong
    )
   
    oferta_existente = session.exec(stmt_existente).first()
    if oferta_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya registraste una oferta para este lote. Podés editar tu oferta existente mientras la convocatoria continúe abierta."
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

@router.put(
    "/{oferta_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)


def update_oferta(
    oferta_id: int,
    oferta_data: OfertaUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Verificar existencia de la oferta
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La oferta con ID {oferta_id} no existe."
        )

    # 2. Verificar que pertenezca a la misma ONG
    if oferta.id_ong != int(current_user['user_id']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permiso para modificar esta oferta."
        )

    # 3. Verificar existencia de lote y emergencia
    lote = session.get(Lote, oferta.id_lote)
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El lote asociado a la oferta no existe."
        )

    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not emergencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La emergencia asociada al lote no existe."
        )

    # 4. Validar vigencia de la convocatoria
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La convocatoria ha expirado. Ya no podés editar esta oferta."
        )

    if oferta_data.cant_recurso <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cantidad ofrecida debe ser mayor a 0."
        )

    # 5. Recalcular espacio disponible excluyendo el valor anterior de esta oferta
    cant_cubierta_sin_esta_oferta = (lote.cantidadCubierta or 0) - oferta.cant_recurso
    cupo_disponible = lote.cantidad - cant_cubierta_sin_esta_oferta

    if oferta_data.cant_recurso > cupo_disponible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La cantidad ingresada supera el faltante del lote. El máximo posible a ofertar es {cupo_disponible} unidades."
        )

    # 6. Aplicar cambios
    oferta.cant_recurso = oferta_data.cant_recurso
    lote.cantidadCubierta = cant_cubierta_sin_esta_oferta + oferta_data.cant_recurso

    if lote.cantidadCubierta >= lote.cantidad:
        lote.estado = "cubierto"
    else:
        lote.estado = "activo"

    session.add(oferta)
    session.add(lote)
    session.commit()
    session.refresh(oferta)
    session.refresh(lote)

    return oferta



@router.get(
    "/misofertas",
    status_code=status.HTTP_200_OK
)
def get_mis_ofertas(
    current_user: dict = Depends(require_roles(REPRESENTANTE_ONG)),
    session: Session = Depends(get_session)
):
    # Extraer el ID del usuario directamente desde el payload JWT
    id_usuario = current_user.get("user_id") or current_user.get("sub")

    if not id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo determinar el ID del usuario autenticado."
        )

    stmt = (
        select(Oferta, Lote, Emergencia)
        .join(Lote, Oferta.id_lote == Lote.id)
        .join(Emergencia, Lote.emergenciaId == Emergencia.id)
        .where(Oferta.id_ong == int(id_usuario))  # Compara contra el user_id (8)
        .order_by(Oferta.id.desc())
    )
    results = session.exec(stmt).all()

    ahora = datetime.now(timezone.utc)

    respuesta = []
    for oferta, lote, emergencia in results:
        fecha_limite = lote.fechaLimiteConvocatoria
        if fecha_limite.tzinfo is None:
            fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)

        vigente = (emergencia.estado == "publicada") and (ahora <= fecha_limite)

        respuesta.append({
            "id": oferta.id,
            "id_lote": oferta.id_lote,
            "cant_recurso": oferta.cant_recurso,
            "id_ong": oferta.id_ong,
            "lote_tipo": lote.tipoRecurso,
            "lote_cantidad_total": lote.cantidad,
            "lote_cantidad_cubierta": lote.cantidadCubierta or 0,
            "emergencia_titulo": emergencia.zonaAfectada,
            "emergencia_estado": emergencia.estado,
            "fecha_limite": fecha_limite.isoformat(),
            "es_editable": vigente
        })

    return respuesta
