from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError
from database import get_session
from dependencies.rbac import require_roles, USUARIO_BONITA
from models.oferta import Oferta
from models.lote import Lote
from models.emergencia import Emergencia
from services.validacion_ofertas import (
    ConvocatoriaAbierta, guardar_resultado, identificador_reserva, preparar_solicitud,
)

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


@router.get('/integraciones/bonita/casos/{caso_id}/lotes/{lote_id}/reservas', dependencies=[Depends(require_roles(USUARIO_BONITA))])
def reservas_caso(caso_id: str, lote_id: int,
                  session: Session = Depends(get_session)):
    emergencia = caso_integracion(caso_id, session)
    lote = session.get(Lote, lote_id)
    if not lote or lote.emergenciaId != emergencia.id:
        raise HTTPException(404, 'El lote no pertenece al caso')
    if lote.estado == 'reformulado':
        raise HTTPException(409, 'El lote ya fue reformulado')
    ofertas = session.exec(select(Oferta).where(
        Oferta.lote_id == lote_id, Oferta.descartada_en.is_(None),
    )).all()
    if not any(o.tarea_bonita_descarte for o in ofertas):
        raise HTTPException(409, 'El lote no tiene un descarte pendiente')
    validadas = [o for o in ofertas if o.validada_en is not None and o.resultado_validacion]
    reservas = {
        o.resultado_validacion.get('reserva_id') or identificador_reserva(
            emergencia, lote, o.ventana_validada or lote.fechaLimiteConvocatoria,
        )
        for o in validadas
    }
    if len(reservas) > 1:
        raise HTTPException(409, 'Hay ofertas activas de distintas ventanas en el lote')
    return {
        'reserva_id': next(iter(reservas)) if reservas else identificador_reserva(
            emergencia, lote, lote.fechaLimiteConvocatoria,
        ),
        'legado': all(not o.resultado_validacion.get('reserva_id') for o in validadas),
        'resultados': [dict(oferta_id=o.id, resultado_validacion=o.resultado_validacion) for o in validadas],
    }
