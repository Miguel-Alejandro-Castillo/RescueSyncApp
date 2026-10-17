from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
import os
import secrets
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError
import httpx
from database import get_session
from dependencies.rbac import require_roles, CENTRO_COORDINADOR, OPERADOR_MUNICIPAL, AUDITORES
from models.oferta import Oferta
from models.lote import Lote
from models.emergencia import Emergencia
from services.nacional_service import get_nacional_service
from services.validacion_ofertas import validar_emergencia, ConvocatoriaAbierta

router = APIRouter(tags=['Validación de ofertas'])


class VincularRecurso(BaseModel):
    codigo: str = Field(min_length=1, max_length=100)


@router.patch('/lotes/{lote_id}/recurso-nacional', dependencies=[Depends(require_roles(CENTRO_COORDINADOR))])
async def vincular_recurso(lote_id: int, data: VincularRecurso,
                          session: Session = Depends(get_session), nacional=Depends(get_nacional_service)):
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(404, 'Lote no encontrado')
    try:
        session.exec(select(Emergencia).where(Emergencia.id == lote.emergenciaId)
                     .with_for_update(nowait=True)).first()
    except OperationalError as error:
        raise HTTPException(409, 'La validación está en curso; reintentá en unos segundos') from error
    if session.exec(select(Oferta).where(Oferta.lote_id == lote_id, Oferta.validada_en != None)).first():
        raise HTTPException(409, 'Este lote ya fue validado; reformulá sus requisitos para cambiar el recurso')
    try:
        catalogo = await nacional.recursos()
    except (httpx.HTTPError, ValueError, KeyError) as error:
        raise HTTPException(502, 'No se pudo consultar el catálogo nacional') from error
    if not any(r['codigo'] == data.codigo for r in catalogo):
        raise HTTPException(422, 'El código no existe en el catálogo nacional')
    lote.recurso_codigo = data.codigo
    session.add(lote)
    session.commit()
    return lote


@router.post('/integraciones/bonita/casos/{caso_id}/validar-ofertas')
async def validar_caso_bonita(caso_id: str, x_validacion_token: str | None = Header(default=None),
                             session: Session = Depends(get_session),
                             nacional=Depends(get_nacional_service)):
    expected = os.getenv('BONITA_VALIDACION_TOKEN', '')
    if not expected:
        raise HTTPException(503, 'La integración de validación con Bonita no está configurada')
    if not x_validacion_token or not secrets.compare_digest(x_validacion_token, expected):
        raise HTTPException(401, 'Credencial de integración inválida')
    emergencia = session.exec(select(Emergencia).where(Emergencia.bonitaCaseId == caso_id)).first()
    if not emergencia:
        raise HTTPException(404, 'El caso de Bonita no tiene una emergencia asociada')
    return await consultar_validacion_nacional(emergencia.id, session, nacional)


@router.get('/recursos-nacionales', dependencies=[Depends(require_roles(CENTRO_COORDINADOR))])
async def recursos_nacionales(nacional=Depends(get_nacional_service)):
    try:
        return await nacional.recursos()
    except (httpx.HTTPError, ValueError, KeyError) as error:
        raise HTTPException(502, 'No se pudo consultar el catálogo nacional') from error


@router.post('/emergencias/{emergencia_id}/validar-ofertas',
             dependencies=[Depends(require_roles(CENTRO_COORDINADOR))])
async def validar_ofertas(emergencia_id: int, session: Session = Depends(get_session),
                         nacional=Depends(get_nacional_service)):
    return (await consultar_validacion_nacional(emergencia_id, session, nacional))['resultados']


async def consultar_validacion_nacional(emergencia_id, session, nacional):
    try:
        return await validar_emergencia(session, emergencia_id, nacional)
    except ConvocatoriaAbierta as error:
        raise HTTPException(409, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except OperationalError as error:
        raise HTTPException(409, 'La validación ya está en curso; reintentá en unos segundos') from error


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
