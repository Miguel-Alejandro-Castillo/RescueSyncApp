from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone
from database import get_session
from pydantic import BaseModel
from typing import List, Optional
from dependencies.rbac import (
    require_roles, REPRESENTANTE_ONG, OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, AUDITORES, USUARIO_BONITA, get_user_roles
)
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import ESTADOS_LOTE_CERRADO, Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from dependencies.jwt_auth import get_current_user
from dependencies.bonita import get_bonita_service
from services.bonita_service import BonitaService, BonitaValidacionService
from services.bonita_service import get_bonita_validacion_service
from services.validacion_ofertas import bloquear_decisiones
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


async def _obtener_cuit_seguro(bonita: BonitaService, user_id: int) -> str:
    """Obtiene y valida el cuitONG del usuario; si usa BonitaValidacionService, garantiza login."""
    if isinstance(bonita, BonitaValidacionService) and not bonita.api_token:
        import os
        auth = await bonita.login(os.getenv("BONITA_USER"), os.getenv("BONITA_PASSWORD"))
        if not auth.get("success"):
            raise HTTPException(502, "No se pudo autenticar la cuenta de servicio de Bonita.")
    return await obtener_cuit_aporte(bonita, user_id)


async def _obtener_ids_misma_ong(bonita: BonitaService, ong_cuit: str, fallback_user_id: int) -> list[int]:
    """Devuelve todos los user_id de REPRESENTANTE_ONG que comparten el mismo cuitONG."""
    ongs = await bonita.obtener_ongs_agrupadas_por_cuit(REPRESENTANTE_ONG)
    for ong in ongs:
        if ong.get("ong_cuit") and ong["ong_cuit"] == ong_cuit:
            return [int(uid) for uid in ong.get("usuario_ids", [])]
    return [int(fallback_user_id)]


def _ong_tiene_participacion_confirmada_en_lote(
    session: Session,
    lote_id: int,
    ong_cuit: str,
    excluir_oferta_id: int | None = None,
) -> bool:
    """Verifica si una ONG (por ong_cuit) ya tiene participación confirmada o liderazgo en el lote."""
    stmt_ofertas = select(Oferta).where(
        Oferta.lote_id == lote_id,
        Oferta.valida == True,
        Oferta.descartada_en.is_(None),
    )
    ofertas_lote = session.exec(stmt_ofertas).all()
    if not ofertas_lote:
        return False

    ofertas_ids = [o.id for o in ofertas_lote if excluir_oferta_id is None or o.id != excluir_oferta_id]
    if not ofertas_ids:
        return False

    stmt_part = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id.in_(ofertas_ids),
        ParticipanteOferta.ong_cuit == ong_cuit,
        ParticipanteOferta.cantidad_aportada.is_not(None),
    )
    return session.exec(stmt_part).first() is not None

class ResponderInvitacion(BaseModel):
    aceptar: bool
    cantidad_aportada: Optional[int] = None  # Obligatorio si acepta


def es_lote_vigente(lote: Lote, emergencia: Emergencia) -> bool:
    fecha_limite = lote.fechaLimiteConvocatoria
    if fecha_limite.tzinfo is None:
        fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
    return lote.estado != LoteEstado.REFORMULADO and datetime.now(timezone.utc) <= fecha_limite


def exigir_oferta_activa(oferta, lote):
    if oferta.descartada_en or lote.estado == LoteEstado.REFORMULADO:
        raise HTTPException(409, "La oferta fue descartada.")
    if oferta.tarea_bonita_descarte:
        raise HTTPException(409, "El descarte de la oferta está en curso.")


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

    if data.cantidad_lider > lote.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tu aporte no puede superar el total requerido por el lote ({lote.cantidad} unidades)."
        )

    ong_cuit = await _obtener_cuit_seguro(bonita, ong_id_actual)

    # Cada ONG (identificada por ong_cuit) solo puede tener una participación confirmada por lote
    if _ong_tiene_participacion_confirmada_en_lote(session, data.id_lote, ong_cuit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu ONG ya está participando en una oferta o consorcio para este lote."
        )

    # 1. Crear la Oferta cabecera
    nueva_oferta = Oferta(
        lote_id=data.id_lote,
        ong_lider_id=ong_id_actual
    )
    session.add(nueva_oferta)
    session.flush()

    # 2. Agregar al líder como participante confirmado con su ong_cuit
    lider_participante = ParticipanteOferta(
        oferta_id=nueva_oferta.id,
        ong_id=ong_id_actual,
        ong_cuit=ong_cuit,
        cantidad_aportada=data.cantidad_lider
    )
    session.add(lider_participante)

    # 3. Registrar invitaciones para todos los miembros de cada ONG invitada (por ong_cuit)
    ongs_bonita = await bonita.obtener_ongs_agrupadas_por_cuit(REPRESENTANTE_ONG)
    user_to_ong = {}
    for ong in ongs_bonita:
        for uid in ong.get("usuario_ids", []):
            user_to_ong[int(uid)] = ong

    invitaciones_creadas: set[tuple[int, str | None]] = set()
    cuits_invitados_unicos: set[str] = set()

    for raw_invitado_id in (data.invitados or []):
        invitado_uid = int(raw_invitado_id)
        ong_invitada = user_to_ong.get(invitado_uid)
        cuit_invitada = ong_invitada.get("ong_cuit") if ong_invitada else await _obtener_cuit_seguro(bonita, invitado_uid)

        # No invitar a la propia ONG
        if cuit_invitada and cuit_invitada == ong_cuit:
            continue
        if not cuit_invitada and invitado_uid == ong_id_actual:
            continue

        usuarios_a_invitar = (
            [int(u) for u in ong_invitada.get("usuario_ids", [])]
            if ong_invitada and cuit_invitada
            else [invitado_uid]
        )

        for uid_miembro in usuarios_a_invitar:
            clave_inv = (uid_miembro, cuit_invitada)
            if clave_inv in invitaciones_creadas:
                continue
            invitaciones_creadas.add(clave_inv)
            session.add(ParticipanteOferta(
                oferta_id=nueva_oferta.id,
                ong_id=uid_miembro,
                ong_cuit=cuit_invitada,
                cantidad_aportada=None
            ))

        if cuit_invitada:
            cuits_invitados_unicos.add(cuit_invitada)

    session.commit()
    mensaje = (
        "Oferta en consorcio creada con éxito"
        if len(cuits_invitados_unicos) > 0
        else "Oferta individual creada con éxito"
    )

    return {"mensaje": mensaje, "oferta_id": nueva_oferta.id}

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
    lote = session.get(Lote, oferta.lote_id)
    exigir_oferta_activa(oferta, lote)
    if not es_lote_vigente(lote, session.get(Emergencia, lote.emergenciaId)):
        raise HTTPException(400, "La convocatoria de este lote ha expirado.")
    
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
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(404, "La oferta no existe.")
    lote = session.get(Lote, oferta.lote_id)
    exigir_oferta_activa(oferta, lote)

    ong_cuit_actual = await _obtener_cuit_seguro(bonita, ong_id_actual)

    stmt = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        (ParticipanteOferta.ong_id == ong_id_actual) | (ParticipanteOferta.ong_cuit == ong_cuit_actual)
    )
    participaciones_ong = session.exec(stmt).all()
    participacion = next(
        (p for p in participaciones_ong if p.cantidad_aportada is None),
        None
    )
    if not participacion:
        raise HTTPException(404, "No tenés ninguna invitación pendiente para esta oferta.")

    # Si rechaza, eliminamos las invitaciones pendientes de esta ONG en esta oferta
    if not data.aceptar:
        for p in participaciones_ong:
            if p.cantidad_aportada is None:
                session.delete(p)
        session.commit()
        return {"mensaje": "Has rechazado la invitación al consorcio."}

    if not data.cantidad_aportada or data.cantidad_aportada <= 0:
        raise HTTPException(status_code=422, detail="Debes indicar una cantidad mayor a 0.")

    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(status_code=400, detail="La convocatoria del lote ha expirado.")

    # Verificar si esta ONG (por ong_cuit) ya participa de forma confirmada en otra oferta del lote
    if _ong_tiene_participacion_confirmada_en_lote(session, oferta.lote_id, ong_cuit_actual, excluir_oferta_id=oferta_id):
        for p in participaciones_ong:
            if p.cantidad_aportada is None:
                session.delete(p)
        session.commit()
        raise HTTPException(
            status_code=400,
            detail="Tu ONG ya tiene una oferta activa o participa de forma confirmada en este lote. Esta invitación ha sido descartada."
        )

    # Calcular cuánto llevan sumado OTRAS ONGs (distinto ong_cuit) en esta oferta
    stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta_id)
    todos_participantes = session.exec(stmt_parts).all()

    suma_otras_ongs = sum(
        p.cantidad_aportada
        for p in todos_participantes
        if p.cantidad_aportada is not None and p.ong_cuit != ong_cuit_actual
    )

    total_propuesto = suma_otras_ongs + data.cantidad_aportada
    if total_propuesto > lote.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"El total de esta oferta ({total_propuesto}) supera el máximo del lote ({lote.cantidad})."
        )

    # Confirmar la participación actual y eliminar las demás invitaciones pendientes de la misma ONG en esta oferta
    participacion.ong_id = ong_id_actual
    participacion.ong_cuit = ong_cuit_actual
    participacion.cantidad_aportada = data.cantidad_aportada
    session.add(participacion)

    for p in participaciones_ong:
        if p.id != participacion.id and p.cantidad_aportada is None:
            session.delete(p)

    session.commit()
    return {"mensaje": "Invitación aceptada y aporte registrado con éxito."}


@router.get(
    "/misofertas-consorcio",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def get_mis_ofertas_consorcio(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_validacion_service),
):
    ong_id_actual = int(current_user['user_id'])
    ong_cuit_actual = await _obtener_cuit_seguro(bonita, ong_id_actual)
    ids_misma_ong = await _obtener_ids_misma_ong(bonita, ong_cuit_actual, ong_id_actual)
    ahora = datetime.now(timezone.utc)

    stmt_participaciones = select(ParticipanteOferta).where(
        (ParticipanteOferta.ong_cuit == ong_cuit_actual) | (ParticipanteOferta.ong_id.in_(ids_misma_ong))
    )
    participaciones = session.exec(stmt_participaciones).all()
    ofertas_ids = [p.oferta_id for p in participaciones]

    stmt_ofertas = select(Oferta).where(
        Oferta.descartada_en.is_(None),
        (Oferta.ong_lider_id.in_(ids_misma_ong)) | (Oferta.id.in_(ofertas_ids if ofertas_ids else [0]))
    )
    ofertas = session.exec(stmt_ofertas).all()

    resultado = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None

        vigente = False
        if lote and lote.fechaLimiteConvocatoria:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            vigente = (lote.estado != LoteEstado.REFORMULADO and ahora <= fecha_limite)

        stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        todos_participantes = session.exec(stmt_parts).all()

        # Agrupar participantes por ong_cuit (para mostrar una entrada por ONG)
        participantes_por_ong: dict[str, dict] = {}
        for p in todos_participantes:
            clave = p.ong_cuit or f"uid-{p.ong_id}"
            if clave not in participantes_por_ong:
                participantes_por_ong[clave] = {
                    "ong_id": p.ong_id,
                    "ong_cuit": p.ong_cuit,
                    "cantidad_aportada": p.cantidad_aportada,
                }
            else:
                # Si ya existía una pendiente y ahora hay una confirmada, priorizamos la confirmada
                if participantes_por_ong[clave]["cantidad_aportada"] is None and p.cantidad_aportada is not None:
                    participantes_por_ong[clave]["cantidad_aportada"] = p.cantidad_aportada
                    participantes_por_ong[clave]["ong_id"] = p.ong_id

        es_lider = oferta.ong_lider_id in ids_misma_ong
        mi_part_confirmada = next(
            (p for p in todos_participantes if (p.ong_cuit == ong_cuit_actual or p.ong_id in ids_misma_ong) and p.cantidad_aportada is not None),
            None
        )
        mi_part_pendiente = next(
            (p for p in todos_participantes if (p.ong_cuit == ong_cuit_actual or p.ong_id in ids_misma_ong) and p.cantidad_aportada is None),
            None
        )

        # Ocultar invitaciones pendientes vencidas
        if not es_lider and mi_part_confirmada is None and mi_part_pendiente is not None and not vigente:
            continue

        es_invitacion_pendiente = (not es_lider and mi_part_confirmada is None and mi_part_pendiente is not None)

        if not es_invitacion_pendiente:
            confirmados_unicos = [v for v in participantes_por_ong.values() if v["cantidad_aportada"] is not None]
            if len(confirmados_unicos) < 2:
                continue

        if es_lider:
            estado_invitacion = "lider"
        elif mi_part_confirmada is not None:
            estado_invitacion = "aceptada"
        else:
            estado_invitacion = "pendiente"

        mi_aporte = (
            mi_part_confirmada.cantidad_aportada
            if mi_part_confirmada is not None
            else (next((p.cantidad_aportada for p in todos_participantes if p.ong_id == oferta.ong_lider_id and p.cantidad_aportada is not None), None) if es_lider else None)
        )

        resultado.append({
            "oferta_id": oferta.id,
            "es_lider": es_lider,
            "estado_invitacion": estado_invitacion,
            "mi_aporte": mi_aporte,
            "lote": lote,
            "emergencia": emergencia,
            "participantes": list(participantes_por_ong.values()),
        })

    return resultado


@router.get(
    "/misofertas",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def get_mis_ofertas_compat(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_validacion_service),
):
    """Devuelve las ofertas confirmadas de la ONG (por ong_cuit) para cualquier representante de esa ONG."""
    ong_id_actual = int(current_user['user_id'])
    ong_cuit_actual = await _obtener_cuit_seguro(bonita, ong_id_actual)
    ids_misma_ong = await _obtener_ids_misma_ong(bonita, ong_cuit_actual, ong_id_actual)

    stmt_participaciones = select(ParticipanteOferta).where(
        (ParticipanteOferta.ong_cuit == ong_cuit_actual) | (ParticipanteOferta.ong_id.in_(ids_misma_ong)),
        ParticipanteOferta.cantidad_aportada != None
    )
    participaciones = session.exec(stmt_participaciones).all()
    ofertas_ids = [p.oferta_id for p in participaciones]

    stmt_ofertas = select(Oferta).where(
        (Oferta.ong_lider_id.in_(ids_misma_ong)) | (Oferta.id.in_(ofertas_ids if ofertas_ids else [0]))
    )
    ofertas = session.exec(stmt_ofertas).all()

    ahora = datetime.now(timezone.utc)
    respuesta = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None

        stmt_parts = select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        todos_participantes = session.exec(stmt_parts).all()

        mi_participacion = next(
            (p for p in todos_participantes if (p.ong_cuit == ong_cuit_actual or p.ong_id in ids_misma_ong) and p.cantidad_aportada is not None),
            None
        )
        if not mi_participacion:
            continue

        if lote and lote.fechaLimiteConvocatoria:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            vigente = (
                not oferta.descartada_en and oferta.valida and lote.estado != LoteEstado.REFORMULADO
                and emergencia is not None and emergencia.estado == EmergenciaEstado.PUBLICADA
                and ahora <= fecha_limite
            )
        else:
            vigente = False

        respuesta.append({
            "id": oferta.id,
            "id_lote": oferta.lote_id,
            "cant_recurso": mi_participacion.cantidad_aportada,
            "id_ong": oferta.ong_lider_id,
            "ong_cuit": mi_participacion.ong_cuit or ong_cuit_actual,
            "lote_tipo": lote.tipoRecurso if lote else "",
            "lote_cantidad_total": lote.cantidad if lote else 0,
            "lote_cantidad_cubierta": lote.cantidadCubierta or 0,
            "emergencia_titulo": emergencia.zonaAfectada if emergencia else "",
            "emergencia_estado": emergencia.estado if emergencia else "",
            "fecha_limite": lote.fechaLimiteConvocatoria.isoformat() if lote and lote.fechaLimiteConvocatoria else "",
            "es_editable": vigente,
            "descartada_en": oferta.descartada_en,
            "motivo_descarte": oferta.motivo_descarte,
        })

    return respuesta

@router.get(
    "/ongs-bonita",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def listar_ongs_desde_bonita(
    current_user: dict = Depends(get_current_user),
    bonita: BonitaService = Depends(get_bonita_validacion_service)
):
    ong_id_actual = int(current_user['user_id'])
    try:
        mi_cuit = await _obtener_cuit_seguro(bonita, ong_id_actual)
        ongs = await bonita.obtener_ongs_agrupadas_por_cuit(REPRESENTANTE_ONG)
        return [
            {
                "id": ong["id"],
                "ong_cuit": ong["ong_cuit"],
                "nombre": ong["nombre"],
            }
            for ong in ongs
            if not (mi_cuit and ong.get("ong_cuit") == mi_cuit) and int(ong["id"]) != ong_id_actual
        ]
    except Exception as e:
        traceback.print_exc()
        print("Error obteniendo usuarios de Bonita:", e)
        raise HTTPException(status_code=500, detail="Error obteniendo usuarios de Bonita.")

@router.put(
    "/{oferta_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
async def editar_aporte_oferta(
    oferta_id: int,
    data: OfertaUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_validacion_service),
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
    exigir_oferta_activa(oferta, lote)

    if not oferta.valida:
        raise HTTPException(status_code=400, detail="La oferta es inválida y no se puede editar.")

    emergencia = session.get(Emergencia, lote.emergenciaId)
    if not es_lote_vigente(lote, emergencia):
        raise HTTPException(status_code=400, detail="La convocatoria de este lote ha expirado.")

    ong_cuit_actual = await _obtener_cuit_seguro(bonita, ong_id_actual)
    ids_misma_ong = await _obtener_ids_misma_ong(bonita, ong_cuit_actual, ong_id_actual)

    stmt = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ((ParticipanteOferta.ong_cuit == ong_cuit_actual) | (ParticipanteOferta.ong_id.in_(ids_misma_ong))),
        ParticipanteOferta.cantidad_aportada.is_not(None)
    )
    participacion = session.exec(stmt).first()
    if not participacion:
        raise HTTPException(status_code=403, detail="Tu ONG no forma parte confirmada de esta oferta.")

    # Sumar lo aportado por las DEMÁS ONGs (distinto ong_cuit)
    stmt_otros = select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta_id,
        ParticipanteOferta.ong_cuit != ong_cuit_actual,
        ParticipanteOferta.cantidad_aportada.is_not(None)
    )
    otros_participantes = session.exec(stmt_otros).all()
    aporte_otros = sum(p.cantidad_aportada for p in otros_participantes if p.cantidad_aportada is not None)

    if (aporte_otros + data.cant_recurso) > lote.cantidad:
        max_permitido = lote.cantidad - aporte_otros
        raise HTTPException(
            status_code=400,
            detail=f"La nueva cantidad supera el límite del lote. Las demás ONGs aportan {aporte_otros}. El máximo posible es {max_permitido}."
        )

    participacion.ong_cuit = participacion.ong_cuit or ong_cuit_actual
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
    exigir_oferta_activa(oferta, session.get(Lote, oferta.lote_id))

    oferta.valida = False
    session.add(oferta)
    session.commit()

    return {"mensaje": "Oferta marcada como inválida."}


@router.get(
    "/invalidas",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
def get_ofertas_invalidas(
    incluir_contexto: bool = False,
    session: Session = Depends(get_session),
):
    filtro = Oferta.valida.is_(False) | Oferta.descartada_en.is_not(None)
    if incluir_contexto:
        lotes_con_invalidas = select(Oferta.lote_id).where(
            Oferta.valida.is_(False), Oferta.descartada_en.is_(None),
        )
        lotes_en_evaluacion = select(Lote.id).join(Emergencia).where(
            Emergencia.estado == EmergenciaEstado.CONVOCATORIA_CERRADA,
            Lote.estado.notin_(ESTADOS_LOTE_CERRADO),
            (Lote.cantidadCubierta < Lote.cantidad) | Lote.id.in_(lotes_con_invalidas),
        )
        filtro |= (
            Oferta.lote_id.in_(lotes_en_evaluacion)
            & Oferta.descartada_en.is_(None)
            & Oferta.validada_en.is_not(None)
        )
    ofertas = session.exec(
        select(Oferta).where(filtro).order_by(Oferta.fecha_creacion.desc(), Oferta.id.desc())
    ).all()

    respuesta = []
    for oferta in ofertas:
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId) if lote else None
        participantes = session.exec(
            select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
        ).all()
        lider = next((p for p in participantes if p.ong_id == oferta.ong_lider_id), None)
        aportes_validados = (oferta.resultado_validacion or {}).get("participantes") or []
        nombre_ong_lider = next(
            (p.get("ong_nombre") for p in aportes_validados if lider and p.get("participante_id") == lider.id),
            None,
        )

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
            "ong_lider_nombre": nombre_ong_lider,
            "cantidad_ofertada": sum(p.cantidad_aportada for p in participantes if p.cantidad_aportada is not None),
            "cantidad_verificada": sum(p.get("cantidad_verificada", 0) or 0 for p in aportes_validados)
            if oferta.validada_en is not None else None,
            "estado_validacion": oferta.estado_validacion,
            "accion_tomada": oferta.accion_tomada,
            "resultado_validacion": oferta.resultado_validacion,
            "validada_en": oferta.validada_en,
            "descartada_en": oferta.descartada_en,
            "motivo_descarte": oferta.motivo_descarte,
        })

    return respuesta


@router.get(
    "/{oferta_id}/detalle",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(OPERADOR_MUNICIPAL, CENTRO_COORDINADOR, REPRESENTANTE_ONG, *AUDITORES))]
)
def get_oferta_detalle(oferta_id: int, session: Session = Depends(get_session)):
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    lote = session.get(Lote, oferta.lote_id)
    participantes = session.exec(
        select(ParticipanteOferta).where(ParticipanteOferta.oferta_id == oferta.id)
    ).all()

    return {
        "id": oferta.id,
        "lote_id": oferta.lote_id,
        "lote_tipo": lote.tipoRecurso if lote else "",
        "lote_descripcion": lote.descripcion if lote else "",
        "lote_cantidad": lote.cantidad if lote else 0,
        "lote_recurso_codigo": lote.recurso_codigo if lote else None,
        "emergencia_id": lote.emergenciaId if lote else None,
        "ong_lider_id": oferta.ong_lider_id,
        "valida": oferta.valida,
        "estado_validacion": oferta.estado_validacion,
        "descartada_en": oferta.descartada_en,
        "motivo_descarte": oferta.motivo_descarte,
        "validada_en": oferta.validada_en,
        "resultado_validacion": oferta.resultado_validacion,
        "accion_tomada": oferta.accion_tomada,
        "participantes": [
            {
                "id": p.id,
                "ong_id": p.ong_id,
                "cantidad_aportada": p.cantidad_aportada,
            }
            for p in participantes
        ]
    }


@router.patch(
    "/{oferta_id}/accion",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def confirmar_accion_oferta_invalida(
    oferta_id: int,
    session: Session = Depends(get_session),
):
    oferta = session.get(Oferta, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="La oferta no existe.")
    lote = session.get(Lote, oferta.lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="El lote de la oferta no existe.")
    raise HTTPException(
        status_code=409,
        detail=f"Las decisiones se toman por emergencia completa. Use POST /lotes/emergencias/{lote.emergenciaId}/decision-invalidas.",
    )

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
    bloquear_decisiones(session, lote.emergenciaId)
    session.refresh(lote)
    if lote.estado != LoteEstado.EN_ADJUDICACION:
        raise HTTPException(409, "El lote no está en adjudicación.")

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

                exigir_oferta_activa(oferta, lote)
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
        lote_pendiente = session.exec(
            select(Lote).where(
                Lote.emergenciaId == lote.emergenciaId,
                Lote.estado.notin_(ESTADOS_LOTE_CERRADO),
            )
        ).first()
        if lote_pendiente is None:
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


@router.post(
    "/limpiar-invitaciones-vencidas",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(USUARIO_BONITA))],
)
def limpiar_invitaciones_vencidas_bonita(
    session: Session = Depends(get_session)
):
    """
    Endpoint invocado por un Timer/Conector REST de Bonita BPM al vencer
    el plazo de convocatoria para eliminar invitaciones pendientes huérfanas.
    """
    ahora = datetime.now(timezone.utc)
    
    stmt_pendientes = select(ParticipanteOferta).where(
        ParticipanteOferta.cantidad_aportada.is_(None)
    )
    participantes_pendientes = session.exec(stmt_pendientes).all()
    
    eliminados = 0
    for p in participantes_pendientes:
        oferta = session.get(Oferta, p.oferta_id)
        if not oferta:
            session.delete(p)
            eliminados += 1
            continue
            
        lote = session.get(Lote, oferta.lote_id)
        if lote and lote.fechaLimiteConvocatoria:
            fecha_limite = lote.fechaLimiteConvocatoria
            if fecha_limite.tzinfo is None:
                fecha_limite = fecha_limite.replace(tzinfo=timezone.utc)
            
            # Si ya venció el plazo o el lote fue reformulado, limpiamos la invitación
            if ahora > fecha_limite or lote.estado == LoteEstado.REFORMULADO:
                session.delete(p)
                eliminados += 1

    if eliminados > 0:
        session.commit()

    return {
        "mensaje": "Limpieza de invitaciones vencidas ejecutada correctamente.",
        "invitaciones_eliminadas": eliminados
    }
