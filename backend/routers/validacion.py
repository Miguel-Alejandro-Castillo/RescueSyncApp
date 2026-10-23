from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError
from database import get_session
from dependencies.rbac import require_roles, CENTRO_COORDINADOR, OPERADOR_MUNICIPAL, AUDITORES, USUARIO_BONITA
from models.oferta import Oferta
from models.lote import Lote
from models.emergencia import Emergencia
from services.validacion_ofertas import preparar_solicitud, guardar_resultado, ConvocatoriaAbierta

router = APIRouter(tags=['Validación de ofertas'])


def caso_integracion(caso_id, session):
    emergencia = session.exec(select(Emergencia).where(Emergencia.bonitaCaseId == caso_id)).first()
    if not emergencia:
        raise HTTPException(404, 'El caso no tiene una emergencia asociada')
    return emergencia


@router.get('/integraciones/bonita/casos/{caso_id}/solicitud-validacion', dependencies=[Depends(require_roles(USUARIO_BONITA))])
def solicitud_validacion(caso_id: str,
                         session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, session)
    try:
        return preparar_solicitud(session, emergencia.id)
    except (ConvocatoriaAbierta, OperationalError) as error:
        session.rollback()
        raise HTTPException(409, str(error)) from error


@router.post('/integraciones/bonita/casos/{caso_id}/resultado-validacion', dependencies=[Depends(require_roles(USUARIO_BONITA))])
def resultado_validacion(caso_id: str, data: dict,
                         session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, session)
    try:
        return guardar_resultado(session, emergencia.id, data)
    except (ValueError, KeyError, TypeError, OperationalError) as error:
        session.rollback()
        raise HTTPException(409, str(error)) from error


def lotes_a_liberar(emergencia, lote_id):
    """Bonita envía un solo lote por decisión; si el coordinador eligió varios, se liberan todos."""
    ultima = (emergencia.decisionesCoordinador or [])[-1:]
    if ultima and lote_id in ultima[0].get('lotes', []):
        return ultima[0]['lotes']
    return [lote_id]


@router.get('/integraciones/bonita/casos/{caso_id}/lotes/{lote_id}/reservas', dependencies=[Depends(require_roles(USUARIO_BONITA))])
def reservas_caso(caso_id: str, lote_id: int,
                  session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, session)
    lote = session.get(Lote, lote_id)
    if not lote or lote.emergenciaId != emergencia.id:
        raise HTTPException(404, 'El lote no pertenece al caso')
    ofertas = session.exec(select(Oferta).where(Oferta.lote_id.in_(lotes_a_liberar(emergencia, lote_id)))).all()
    return {'resultados': [dict(oferta_id=o.id, resultado_validacion=o.resultado_validacion)
                           for o in ofertas if o.validada_en is not None and o.resultado_validacion]}



@router.get('/ofertas-validacion', dependencies=[Depends(require_roles(
    CENTRO_COORDINADOR, OPERADOR_MUNICIPAL, *AUDITORES))])
def resultados_validacion(emergencia_id: int | None = None, session: Session = Depends(get_session)):
    query = select(Oferta, Lote, Emergencia).join(Lote, Oferta.lote_id == Lote.id).join(
        Emergencia, Lote.emergenciaId == Emergencia.id)
    if emergencia_id is not None:
        query = query.where(Lote.emergenciaId == emergencia_id)
    return [{
        'id': oferta.id, 'emergencia_id': lote.emergenciaId,
        'lote_id': lote.id, 'lote_descripcion': lote.descripcion,
        'lote_cantidad': lote.cantidad, 'emergencia_zona': emergencia.zonaAfectada,
        'emergencia_gravedad': emergencia.nivelGravedad,
        'recurso_codigo': lote.recurso_codigo, 'estado_validacion': oferta.estado_validacion,
        'validada_en': oferta.validada_en, 'resultado_validacion': oferta.resultado_validacion,
        'decisiones_coordinador': emergencia.decisionesCoordinador,
    } for oferta, lote, emergencia in session.exec(query.order_by(Oferta.id)).all()]
