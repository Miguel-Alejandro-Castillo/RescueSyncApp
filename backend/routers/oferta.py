from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone
from database import get_session
from pydantic import BaseModel
from typing import List, Optional
from dependencies.rbac import (
    require_roles, REPRESENTANTE_ONG, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, AUDITORES, get_user_roles
)
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from dependencies.jwt_auth import get_current_user
from dependencies.bonita import get_bonita_service
from services.bonita_service import BonitaService
from services.bonita_service import get_bonita_validacion_service
from fastapi import Response
import traceback
import httpx

router = APIRouter(
    prefix="/ofertas",
    tags=["ofertas"]
)

# --- SCHEMAS PYDANTIC PARA VALIDACIÓN DE ENTRADA ---
class ParticipanteCreate(BaseModel):
    ong_id: int
    cantidad_aportada: Optional[int] = None  # Si es None, queda como invitación pendiente

class OfertaConsorcioCreate(BaseModel):
    id_lote: int
    cantidad_lider: int  # Lo que aporta la ONG líder inicialmente
    invitados: Optional[List[int]] = []  # IDs de otras ONGs a invitar
class OfertaUpdate(BaseModel):
    cant_recurso: int
    id_ong: Optional[int] = None

class AdjudicacionDetalleRequest(BaseModel):
    participante_id: int
    cantidad_adjudicada: int


class AdjudicacionRequest(BaseModel):
    detalles: list[AdjudicacionDetalleRequest]

class AccionOfertaInvalida(BaseModel):
    accion: str

ACCIONES_OFERTA_INVALIDA = ["reabrir", "reformular", "parcial"]


async def obtener_cuit_aporte(bonita, user_id):
    try:
        cuit = await bonita.obtener_cuit_ong(user_id)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(502, "No se pudo identificar la ONG del representante. Reintentá el aporte.") from error
    cuit = (cuit or '').strip()
    if not cuit:
        raise HTTPException(422, "El representante no tiene cuitONG configurado en Bonita.")
    if len(cuit) > 32:
        raise HTTPException(422, "El cuitONG configurado en Bonita no es válido.")
    return cuit

class ResponderInvitacion(BaseModel):
    aceptar: bool
    cantidad_aportada: Optional[int] = None  # Obligatorio si acepta


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
    statement = select(Emergencia).where(Emergencia.estado == EmergenciaEstado.PUBLICADA).order_by(
        Emergencia.fechaCreacion.desc(), Emergencia.id.desc()
    )
    emergencias = session.exec(statement).all()
    
    resultado = []
    for emergencia in emergencias:
        stmt_lotes = select(Lote).where(Lote.emergenciaId == emergencia.id).order_by(
            Lote.fechaCreacion.desc(), Lote.id.desc()
        )
        if REPRESENTANTE_ONG in get_user_roles(current_user):
            stmt_lotes = stmt_lotes.where(Lote.estado.in_([LoteEstado.CREADO, LoteEstado.ACTIVO, LoteEstado.ABIERTO]))
        
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
async def create_oferta_consorcio(
    data: OfertaConsorcioCreate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_validacion_service),
):
    ong_id_actual = int(current_user['user_id'])

    if data.cantidad_lider <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cantidad ofrecida debe ser mayor a 0."
        )

    lote = session.get(Lote, data.id_lote)
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")

    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(status_code=400, detail="La convocatoria de este lote ha expirado.")

    
    stmt_ofertas_lote = select(Oferta).where(Oferta.lote_id == data.id_lote, Oferta.valida == True)
    ofertas_en_lote = session.exec(stmt_ofertas_lote).all()
    ofertas_ids = [o.id for o in ofertas_en_lote]

    if ofertas_ids:
        stmt_participacion_previa = select(ParticipanteOferta).where(
            ParticipanteOferta.oferta_id.in_(ofertas_ids),
            ParticipanteOferta.ong_id == ong_id_actual
        )
        if session.exec(stmt_participacion_previa).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya estás participando en una oferta o consorcio para este lote."
            )
    # Cada oferta puede pedir hasta el total del lote de forma independiente
    if data.cantidad_lider > lote.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tu aporte no puede superar el total requerido por el lote ({lote.cantidad} unidades)."
        )

    ong_cuit = await obtener_cuit_aporte(bonita, ong_id_actual)

    # 1. Crear la Oferta cabecera
    nueva_oferta = Oferta(
        lote_id=data.id_lote,
        ong_lider_id=ong_id_actual
    )
    session.add(nueva_oferta)
    session.flush()

    # 2. Agregar al líder como participante confirmado
    lider_participante = ParticipanteOferta(
        oferta_id=nueva_oferta.id,
        ong_id=ong_id_actual,
        ong_cuit=ong_cuit,
        cantidad_aportada=data.cantidad_lider
    )
    session.add(lider_participante)

    # 3. Registrar invitaciones a otras ONGs
    for ong_invitada_id in data.invitados:
        if ong_invitada_id == ong_id_actual:
            continue
        invitacion = ParticipanteOferta(
            oferta_id=nueva_oferta.id,
            ong_id=ong_invitada_id,
            cantidad_aportada=None
        )
        session.add(invitacion)

    session.commit()
    return {"mensaje": "Oferta en consorcio creada con éxito", "oferta_id": nueva_oferta.id}


@router.post(
    "/{oferta_id}/invitar",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def invitar_ong_a_oferta(
    oferta_id: int,
    data: ParticipanteCreate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta no existe.")
    
    if oferta.ong_lider_id != int(current_user['user_id']):
        raise HTTPException(status_code=403, detail="Solo la ONG líder puede invitar a otros.")

    stmt = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ParticipanteOferta.ong_id == data.ong_id
    )
    existente = session.exec(stmt).first()
    if existente:
        raise HTTPException(status_code=400, detail="Esta ONG ya fue invitada o forma parte de la oferta.")

    nuevo_participante = ParticipanteOferta(
        oferta_id=oferta_id,
        ong_id=data.ong_id,
        cantidad_aportada=None
    )
    session.add(nuevo_participante)
    session.commit()
    return {"mensaje": "Invitación enviada correctamente."}


@router.post(
    "/{oferta_id}/responder-invitacion",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def responder_invitacion(
    oferta_id: int,
    data: ResponderInvitacion,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_validacion_service),
):
    ong_id_actual = int(current_user['user_id'])

    stmt = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ParticipanteOferta.ong_id == ong_id_actual
    )
    participacion = session.exec(stmt).first()
    if not participacion:
        raise HTTPException(status_code=404, detail="No tenés ninguna invitación pendiente para esta oferta.")

    if not data.aceptar:
        session.delete(participacion)
        session.commit()
        return {"mensaje": "Has rechazado la invitación al consorcio."}

    if not data.cantidad_aportada or data.cantidad_aportada <= 0:
        raise HTTPException(status_code=422, detail="Debes indicar una cantidad mayor a 0.")

    oferta = session.get(Oferta, oferta_id)
    lote = session.get(Lote, oferta.lote_id)
    emergencia = session.get(Emergencia, lote.emergenciaId)

    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(status_code=400, detail="La convocatoria del lote ha expirado.")

    # Calcular cuánto lleva sumado ESTA oferta en consorcio en total
    stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta_id)
    todos_participantes = session.exec(stmt_parts).all()
    
    aporte_anterior = participacion.cantidad_aportada or 0
    suma_actual_oferta = sum(p.cantidad_aportada for p in todos_participantes if p.cantidad_aportada is not None and p.ong_id != ong_id_actual)
    
    total_propuesto = suma_actual_oferta + data.cantidad_aportada
    if total_propuesto > lote.cantidad:
        raise HTTPException(
            status_code=400, 
            detail=f"El total de esta oferta ({total_propuesto}) supera el máximo del lote ({lote.cantidad})."
        )

    if participacion.cantidad_aportada is None:
        participacion.ong_cuit = await obtener_cuit_aporte(bonita, ong_id_actual)
    elif not participacion.ong_cuit:
        raise HTTPException(409, "Debe revisarse la ONG de origen del aporte antes de modificarlo.")
    participacion.cantidad_aportada = data.cantidad_aportada
    session.add(participacion)
    session.commit()

    return {"mensaje": "Invitación aceptada y aporte registrado con éxito."}


@router.get(
    "/misofertas-consorcio",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def get_mis_ofertas_consorcio(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    ong_id_actual = int(current_user['user_id'])

    stmt_participaciones = select(ParticipanteOferta).where(ParticipanteOferta.ong_id == ong_id_actual)
    participaciones = session.exec(stmt_participaciones).all()
    ofertas_ids = [p.oferta_id for p in participaciones]

    stmt_ofertas = select(Oferta).where(
        (Oferta.ong_lider_id == ong_id_actual) | (Oferta.id.in_(ofertas_ids if ofertas_ids else [0]))
    )
    ofertas = session.exec(stmt_ofertas).all()

    resultado = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None
        
        stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        todos_participantes = session.exec(stmt_parts).all()

        es_lider = (oferta.ong_lider_id == ong_id_actual)
        mi_participacion = next((p for p in todos_participantes if p.ong_id == ong_id_actual), None)
        estado_invitacion = "lider" if es_lider else ("pendiente" if mi_participacion and mi_participacion.cantidad_aportada is None else "aceptada")

        resultado.append({
            "oferta_id": oferta.id,
            "es_lider": es_lider,
            "estado_invitacion": estado_invitacion,
            "mi_aporte": mi_participacion.cantidad_aportada if mi_participacion else None,
            "lote": lote,
            "emergencia": emergencia,
            "participantes": [
                {"ong_id": p.ong_id, "cantidad_aportada": p.cantidad_aportada} 
                for p in todos_participantes
            ]
        })

    return resultado


@router.get(
    "/misofertas",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def get_mis_ofertas_compat(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Endpoint de compatibilidad para el frontend que consulta /misofertas"""
    ong_id_actual = int(current_user['user_id'])
    
    # 1. Traer solo las participaciones confirmadas (donde cantidad_aportada NO sea None)
    stmt_participaciones = select(ParticipanteOferta).where(
        ParticipanteOferta.ong_id == ong_id_actual,
        ParticipanteOferta.cantidad_aportada != None
    )
    participaciones = session.exec(stmt_participaciones).all()
    ofertas_ids = [p.oferta_id for p in participaciones]

    # 2. Traer las ofertas donde el usuario sea líder o tenga una participación confirmada
    stmt_ofertas = select(Oferta).where(
        (Oferta.ong_lider_id == ong_id_actual) | (Oferta.id.in_(ofertas_ids if ofertas_ids else [0]))
    )
    ofertas = session.exec(stmt_ofertas).all()

    ahora = datetime.now(timezone.utc)
    respuesta = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None
        
        stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        todos_participantes = session.exec(stmt_parts).all()
        mi_participacion = next((p for p in todos_participantes if p.ong_id == ong_id_actual), None)

        # 3. Ignorar invitaciones pendientes de respuesta
        if not mi_participacion or mi_participacion.cantidad_aportada is None:
            continue

        if lote and lote.fechaLimiteConvocatoria:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            vigente = (emergencia and emergencia.estado == EmergenciaEstado.PUBLICADA) and (ahora <= fecha_limite)
        else:
            vigente = False

        respuesta.append({
            "id": oferta.id,
            "id_lote": oferta.lote_id,
            "cant_recurso": mi_participacion.cantidad_aportada,
            "id_ong": oferta.ong_lider_id,
            "lote_tipo": lote.tipoRecurso if lote else "",
            "lote_cantidad_total": lote.cantidad if lote else 0,
            "lote_cantidad_cubierta": lote.cantidadCubierta or 0,
            "emergencia_titulo": emergencia.zonaAfectada if emergencia else "",
            "emergencia_estado": emergencia.estado if emergencia else "",
            "fecha_limite": lote.fechaLimiteConvocatoria.isoformat() if lote and lote.fechaLimiteConvocatoria else "",
            "es_editable": vigente
        })

    return respuesta

@router.get(
    "/ongs-bonita",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def listar_ongs_desde_bonita(
    current_user: dict = Depends(get_current_user),
    bonita: BonitaService = Depends(get_bonita_service)
):
    ong_id_actual = int(current_user['user_id'])
    try:
        # Usamos el método del servicio BonitaService para obtener los usuarios con el rol "representante_ong"
        usuarios = await bonita.obtener_usuarios_por_rol(REPRESENTANTE_ONG)
       
        resultado = []

        for u in usuarios:

            uid = int(u.get("id", 0))

            # Filtrar para no mostrar a la ONG actual

            if uid != ong_id_actual:
                firstname = u.get('firstname', '') or ''
                lastname = u.get('lastname', '') or ''
                nombre_completo = f"{firstname} {lastname}".strip()
                nombre = nombre_completo if nombre_completo else u.get('userName', f"ONG #{uid}")
                resultado.append({
                    "id": uid,
                    "nombre": nombre
                })

        return resultado

    except Exception as e:
        traceback.print_exc()
        print("Error obteniendo usuarios de Bonita:", e)
        raise HTTPException(status_code=500, detail="Error obteniendo usuarios de Bonita.")

@router.put(
    "/{oferta_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def editar_aporte_oferta(
    oferta_id: int,
    data: OfertaUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    ong_id_actual = int(current_user['user_id'])

    if data.cant_recurso <= 0:
        raise HTTPException(status_code=422, detail="La cantidad debe ser mayor a 0.")

    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta no existe.")

    lote = session.get(Lote, oferta.lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="El lote asociado no existe.")

    if not oferta.valida:
        raise HTTPException(status_code=400, detail="La oferta es inválida y no se puede editar.")

    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(status_code=400, detail="La convocatoria de este lote ha expirado.")

    # Buscar la participación de la ONG actual en esta oferta
    stmt = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ParticipanteOferta.ong_id == ong_id_actual
    )
    participacion = session.exec(stmt).first()
    if not participacion:
        raise HTTPException(status_code=403, detail="No formas parte de esta oferta en consorcio.")

    # 1. Sumar lo aportado por los DEMÁS miembros de la oferta (excluyendo al usuario actual)
    stmt_otros = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ParticipanteOferta.ong_id != ong_id_actual
    )
    otros_participantes = session.exec(stmt_otros).all()
    aporte_otros = sum(p.cantidad_aportada for p in otros_participantes if p.cantidad_aportada is not None)

    # 2. Verificar que el nuevo aporte + lo aportado por los demás no supere el total del lote
    if (aporte_otros + data.cant_recurso) > lote.cantidad:
        max_permitido = lote.cantidad - aporte_otros
        raise HTTPException(
            status_code=400,
            detail=f"La nueva cantidad supera el límite del lote. Los demás miembros aportan {aporte_otros}. Tu máximo posible es {max_permitido}."
        )

    if not participacion.ong_cuit:
        raise HTTPException(409, "Debe revisarse la ONG de origen del aporte antes de modificarlo.")

    # 3. Guardar el nuevo aporte
    participacion.cantidad_aportada = data.cant_recurso
    session.add(participacion)
    session.commit()

    return {"mensaje": "Aporte actualizado correctamente en el consorcio."}

@router.patch(
    "/{oferta_id}/invalida",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
def marcar_oferta_invalida(
    oferta_id: int,
    session: Session = Depends(get_session)
):
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta no existe.")

    oferta.valida = False
    session.add(oferta)
    session.commit()

    return {"mensaje": "Oferta marcada como inválida."}


@router.get(
    "/invalidas",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
def get_ofertas_invalidas(session: Session = Depends(get_session)):
    ofertas = session.exec(select(Oferta).where(Oferta.valida == False)).all()

    respuesta = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None
        participantes = session.exec(
            select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        ).all()

        convocatoria_abierta = False
        if lote:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            convocatoria_abierta = datetime.now(timezone.utc) <= fecha_limite

        lotes_nuevos = session.exec(
            select(Lote).where(Lote.loteOrigenId == oferta.lote_id)
        ).all()

        respuesta.append({
            "id": oferta.id,
            "id_lote": oferta.lote_id,
            "lote_tipo": lote.tipoRecurso if lote else "",
            "lote_descripcion": lote.descripcion if lote else "",
            "lote_cantidad": lote.cantidad if lote else 0,
            "lote_estado": lote.estado if lote else "",
            "convocatoria_abierta": convocatoria_abierta,
            "lotes_nuevos": [
                {
                    "id": nuevo.id,
                    "tipo": nuevo.tipoRecurso,
                    "descripcion": nuevo.descripcion,
                    "cantidad": nuevo.cantidad,
                    "cantidad_cubierta": nuevo.cantidadCubierta
                }
                for nuevo in lotes_nuevos
            ],
            "emergencia_id": emergencia.id if emergencia else None,
            "emergencia_zona": emergencia.zonaAfectada if emergencia else "",
            "ong_lider_id": oferta.ong_lider_id,
            "cantidad_ofertada": sum(p.cantidad_aportada for p in participantes if p.cantidad_aportada is not None),
            "accion_tomada": oferta.accion_tomada,
            "resultado_validacion": oferta.resultado_validacion,
            "validada_en": oferta.validada_en,
        })

    return respuesta


@router.patch(
    "/{oferta_id}/accion",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def confirmar_accion_oferta_invalida(
    oferta_id: int,
    data: AccionOfertaInvalida,
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_service),
):
    if data.accion not in ACCIONES_OFERTA_INVALIDA:
        raise HTTPException(status_code=422, detail="La acción no es válida.")

    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta no existe.")

    if oferta.valida:
        raise HTTPException(status_code=400, detail="La oferta es válida, no requiere acción.")

    if oferta.accion_tomada:
        raise HTTPException(status_code=400, detail="Ya se confirmó una acción para esta oferta.")

    if data.accion == "parcial":
        resultado = oferta.resultado_validacion
        if not resultado or resultado.get('error') or oferta.estado_validacion == 'pendiente':
            raise HTTPException(status_code=409, detail="Primero debe completarse la consulta de recursos para aceptar una cantidad parcial.")
        if resultado.get('cantidad_verificada', 0) <= 0:
            raise HTTPException(status_code=400, detail="No hay recursos disponibles para aceptar una cobertura parcial.")
        # Conservar lo prometido y aceptar sólo la cantidad respaldada por inventario.
        resultado = dict(resultado)
        resultado['cantidad_aceptada'] = resultado['cantidad_verificada']
        resultado['participantes'] = [{**p, 'cantidad_aceptada': p['cantidad_verificada']}
                                     for p in resultado.get('participantes', [])]
        oferta.resultado_validacion = resultado

    oferta.accion_tomada = data.accion
    session.add(oferta)

    if data.accion == "parcial":
        lote_oferta = session.get(Lote, oferta.lote_id)
        ahora = datetime.now(timezone.utc)
        lotes = session.exec(
            select(Lote).where(
                Lote.emergenciaId == lote_oferta.emergenciaId,
                Lote.estado != LoteEstado.REFORMULADO
            )
        ).all()
        for lote in lotes:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            if fecha_limite > ahora:
                lote.fechaLimiteConvocatoria = ahora
                session.add(lote)

    if data.accion == "parcial":
        emergencia = session.get(Emergencia, lote_oferta.emergenciaId)
        if not emergencia or not emergencia.bonitaCaseId:
            session.rollback()
            raise HTTPException(409, "Esta emergencia no tiene un caso asociado en Bonita.")
        try:
            await bonita.resolver_accion_coordinador(emergencia.bonitaCaseId, "ACEPTAR_OFERTAS")
        except Exception:
            session.rollback()
            raise

    session.commit()

    return {"mensaje": "Acción confirmada correctamente."}

class AdjudicacionDetalleRequest(BaseModel):
    participante_id: int
    cantidad_adjudicada: int
class AdjudicacionRequest(BaseModel):
    detalles: list[AdjudicacionDetalleRequest]


@router.post(
    "/{lote_id}/adjudicaciones",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL))]
)
async def adjudicar_ofertas(
    lote_id: int,
    data: list[AdjudicacionRequest],
    current_user: dict = Depends(get_current_user),
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session),
):
    lote: Lote | None = session.get(Lote, lote_id)

    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El lote no existe."
        )

    # Validar cantidades antes de realizar modificaciones
    total_adjudicado = 0
    hay_detalles = False

    for adjudicacion in data:
        for detalle in adjudicacion.detalles:

            if detalle.cantidad_adjudicada <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La cantidad adjudicada debe ser mayor a 0."
                )

            hay_detalles = True
            total_adjudicado += detalle.cantidad_adjudicada

    if not hay_detalles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe adjudicar al menos una cantidad antes de confirmar."
        )

    if total_adjudicado > lote.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cantidad adjudicada excede la cantidad requerida del lote."
        )

    try:
        for adjudicacion in data:

            # Crear la adjudicación
            adjudicacion_model = Adjudicacion(
                lote_id=lote_id,
                usuario_id=str(current_user["user_id"]),
            )

            session.add(adjudicacion_model)

            # Necesitamos el ID generado antes de crear los detalles
            session.flush()

            for detalle in adjudicacion.detalles:

                participante_oferta = session.get(
                    ParticipanteOferta,
                    detalle.participante_id
                )

                if not participante_oferta:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=(
                            f"La oferta del participante "
                            f"{detalle.participante_id} no existe."
                        )
                    )

                oferta = session.get(
                    Oferta,
                    participante_oferta.oferta_id
                )

                if not oferta or oferta.lote_id != lote_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"La participación {detalle.participante_id} "
                            f"no pertenece al lote {lote_id}."
                        )
                    )

                adjudicacion_detalle = AdjudicacionDetalle(
                    adjudicacion_id=adjudicacion_model.id,
                    participante_oferta_id=participante_oferta.id,
                    cantidad_adjudicada=detalle.cantidad_adjudicada,
                )

                session.add(adjudicacion_detalle)                

        # El lote se actualiza una única vez después de procesar correctamente todas las adjudicaciones.
        lote.estado = LoteEstado.ADJUDICADO
        session.add(lote)
        # Hacer explícito que el nuevo estado llegue a BD dentro de la transacción
        # antes de consultar los demás lotes.
        session.flush()
        # buscar todos los lotes de la emergencia y validar que todos estan correctamente en estado ADJUDICADO
        lote_no_adjudicado = session.exec(
            select(Lote).where(Lote.emergenciaId == lote.emergenciaId, Lote.estado != LoteEstado.ADJUDICADO)
        ).first()
        if not lote_no_adjudicado:
            # estan todos los lotes adjudicados, se completa la tarea humana en Bonita
            emergencia: Emergencia = session.get(Emergencia, lote.emergenciaId)
            if emergencia.bonitaCaseId:
                await bonita.completar_tarea_humana_por_caso(emergencia.bonitaCaseId)
            emergencia.estado = EmergenciaEstado.ADJUDICADA
            session.add(emergencia)

        session.commit()
    except httpx.HTTPStatusError as e:
        session.rollback()
        print(f"HTTP STATUS ERROR: {repr(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la comunicación HTTP: {str(e)}"
        ) from e
    
    except HTTPException:
        session.rollback()
        raise

    except Exception as error:
        session.rollback()

        print(f"ERROR ADJUDICANDO: {repr(error)}")
        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al adjudicar ofertas: {str(error)}"
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)