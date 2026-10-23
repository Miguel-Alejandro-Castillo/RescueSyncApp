from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from database import get_session
from dependencies.jwt_auth import get_current_user
from dependencies.rbac import require_roles, REPRESENTANTE_ONG
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote
from models.participante_oferta import ParticipanteOferta
from models.trabajo_finalizado import TrabajoFinalizado
from services.ejecucion import ongs_adjudicadas

router = APIRouter(
    prefix="/ejecucion",
    tags=["ejecución"],
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)


def cuit_representante(current_user: dict) -> str:
    cuit = (current_user.get("cuitONG") or "").strip()
    if not cuit:
        raise HTTPException(status_code=422, detail="El representante no tiene cuitONG configurado en Bonita.")
    return cuit


@router.get("/mis-emergencias")
def get_mis_emergencias_adjudicadas(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    cuit = cuit_representante(current_user)
    emergencias_ids = session.exec(
        select(Lote.emergenciaId).distinct()
        .join(Adjudicacion, Adjudicacion.lote_id == Lote.id)
        .join(AdjudicacionDetalle, AdjudicacionDetalle.adjudicacion_id == Adjudicacion.id)
        .join(ParticipanteOferta, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
        .where(ParticipanteOferta.ong_cuit == cuit)
    ).all()

    respuesta = []
    for emergencia in session.exec(
        select(Emergencia).where(Emergencia.id.in_(emergencias_ids)).order_by(Emergencia.fechaCreacion.desc())
    ).all():
        mi_ong = next(o for o in ongs_adjudicadas(session, emergencia.id) if o["cuit"] == cuit)
        respuesta.append({
            "id": emergencia.id,
            "zona": emergencia.zonaAfectada,
            "estado": emergencia.estado,
            "lotes": mi_ong["lotes"],
            "finalizado_en": mi_ong["finalizado_en"],
            # Sólo se informa durante la ejecución: todos los lotes adjudicados y el monitoreo abierto.
            "en_ejecucion": emergencia.estado == EmergenciaEstado.ADJUDICADA,
        })
    return respuesta


@router.post("/emergencias/{emergencia_id}/trabajo-finalizado", status_code=status.HTTP_201_CREATED)
def marcar_trabajo_finalizado(
    emergencia_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    cuit = cuit_representante(current_user)
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="La emergencia no existe.")

    if not any(o["cuit"] == cuit for o in ongs_adjudicadas(session, emergencia_id)):
        raise HTTPException(status_code=403, detail="Tu ONG no tiene recursos adjudicados en esta emergencia.")
    if emergencia.estado != EmergenciaEstado.ADJUDICADA:
        raise HTTPException(status_code=409, detail="La emergencia no está en ejecución.")

    trabajo = TrabajoFinalizado(emergencia_id=emergencia_id, ong_cuit=cuit, usuario_id=str(current_user["user_id"]))
    session.add(trabajo)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Tu ONG ya informó que terminó su trabajo en esta emergencia.")
    session.refresh(trabajo)
    return trabajo
