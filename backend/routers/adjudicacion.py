from pydantic import BaseModel
from dependencies.rbac import require_roles, USUARIO_BONITA
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.participante_oferta import ParticipanteOferta
from models.lote import Lote
from fastapi import Depends
from sqlmodel import Session
from database import get_session
from fastapi import APIRouter

router = APIRouter(
    prefix="/adjudicaciones",
    tags=["adjudicaciones"]
)

class AdjudicacionDetalleResponse(BaseModel):
    cuit_ong: str | None = None # despues quitar el None
    cantidad_adjudicada: int | None = None # despues quitar el None

class AdjudicacionResponse(BaseModel):
    nombre_recurso: str
    detalles: list[AdjudicacionDetalleResponse]

@router.get("/emergencia/{emergencia_id}", dependencies=[Depends(require_roles(USUARIO_BONITA))])
def obtener_adjudicaciones_por_emergencia(
	emergencia_id: int,
    session: Session = Depends(get_session)
) -> list[AdjudicacionResponse]:
	"""Obtiene todas las adjudicaciones de una emergencia y sus detalles."""
	adjudicaciones = (
		session.query(Adjudicacion, Lote)
		.join(Lote, Adjudicacion.lote_id == Lote.id)
		.filter(Lote.emergenciaId == emergencia_id)
		.all()
	)

	resultado = []
	for adjudicacion, lote in adjudicaciones:
		detalles = (
			session.query(AdjudicacionDetalle, ParticipanteOferta)
			.join(ParticipanteOferta, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
			.filter(AdjudicacionDetalle.adjudicacion_id == adjudicacion.id)
			.all()
		)
		# A FUTURO el recurso deberia pasarse como codigo
		resultado.append(AdjudicacionResponse(
			nombre_recurso=lote.descripcion,
			detalles=[AdjudicacionDetalleResponse(cuit_ong=participante_oferta.ong_cuit, cantidad_adjudicada=adjudicacion_detalle.cantidad_adjudicada) for adjudicacion_detalle, participante_oferta in detalles]
		))

	return resultado



