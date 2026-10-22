from fastapi import APIRouter, Depends, HTTPException, Header
import os
import secrets
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError
from database import get_session
from dependencies.rbac import require_roles, CENTRO_COORDINADOR, OPERADOR_MUNICIPAL, AUDITORES
from models.oferta import Oferta
from models.lote import Lote
from models.emergencia import Emergencia
from services.validacion_ofertas import preparar_solicitud, guardar_resultado, ConvocatoriaAbierta

router = APIRouter(tags=['Validación de ofertas'])


def caso_integracion(caso_id, token, session):
    expected = os.getenv('BONITA_VALIDACION_TOKEN', '')
    if not expected:
        raise HTTPException(503, 'La integración de validación con Bonita no está configurada')
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(401, 'Credencial de integración inválida')
    emergencia = session.exec(select(Emergencia).where(Emergencia.bonitaCaseId == caso_id)).first()
    if not emergencia:
        raise HTTPException(404, 'El caso no tiene una emergencia asociada')
    return emergencia


@router.get('/integraciones/bonita/casos/{caso_id}/solicitud-validacion')
def solicitud_validacion(caso_id: str, x_validacion_token: str | None = Header(default=None),
                         session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, x_validacion_token, session)
    try:
        return preparar_solicitud(session, emergencia.id)
    except (ConvocatoriaAbierta, OperationalError) as error:
        session.rollback()
        raise HTTPException(409, str(error)) from error


@router.post('/integraciones/bonita/casos/{caso_id}/resultado-validacion')
def resultado_validacion(caso_id: str, data: dict, x_validacion_token: str | None = Header(default=None),
                         session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, x_validacion_token, session)
    try:
        return guardar_resultado(session, emergencia.id, data)
    except (ValueError, KeyError, TypeError, OperationalError) as error:
        session.rollback()
        raise HTTPException(409, str(error)) from error


@router.get('/integraciones/bonita/casos/{caso_id}/lotes/{lote_id}/reservas')
def reservas_caso(caso_id: str, lote_id: int, x_validacion_token: str | None = Header(default=None),
                  session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, x_validacion_token, session)
    lote = session.get(Lote, lote_id)
    if not lote or lote.emergenciaId != emergencia.id:
        raise HTTPException(404, 'El lote no pertenece al caso')
    ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote_id)).all()
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
        'accion_tomada': oferta.accion_tomada,
    } for oferta, lote, emergencia in session.exec(query.order_by(Oferta.id)).all()]
