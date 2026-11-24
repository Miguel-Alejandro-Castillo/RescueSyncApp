from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from models.emergencia import EmergenciaEstado
from models.lote import ESTADOS_LOTE_CERRADO, Lote, LoteEstado
from models.oferta import Oferta, OfertaEstado
from services.validacion_ofertas import descartar_ofertas, resultado_guardado, utc


class CantidadLoteRequest(BaseModel):
    lote_id: int
    cantidad: int = Field(gt=0)


class DecisionOfertasInvalidasEmergencia(BaseModel):
    accion: Literal['reabrir', 'reformular', 'parcial']
    lote_ids: list[int] = Field(default_factory=list)
    lotes: list[CantidadLoteRequest] = Field(default_factory=list)


class DecisionConvocatoriaBonita(DecisionOfertasInvalidasEmergencia):
    accion: Literal['reabrir', 'reformular']
    tarea_id: str = Field(pattern=r'^[0-9]{1,32}$')
    ventana_ms: int = Field(gt=0)
    fecha_limite: datetime | None = None


def lotes_pendientes(session, emergencia_id):
    return session.exec(select(Lote).where(
        Lote.emergenciaId == emergencia_id,
        Lote.estado.notin_(ESTADOS_LOTE_CERRADO),
    ).order_by(Lote.id)).all()


def ofertas_vigentes(session, lotes):
    return session.exec(select(Oferta).where(
        Oferta.lote_id.in_([lote.id for lote in lotes]), Oferta.descartada_en.is_(None),
    )).all()


def lotes_con_faltante(lotes):
    return {lote.id for lote in lotes if lote.cantidadCubierta < lote.cantidad}


def lotes_con_recursos_verificados(ofertas):
    return {
        oferta.lote_id for oferta in ofertas
        if any(p.get('cantidad_verificada', 0) > 0
               for p in (oferta.resultado_validacion or {}).get('participantes', []))
    }


def validacion_completa(ofertas):
    return all(
        oferta.validada_en is not None
        and oferta.estado_validacion in (OfertaEstado.VALIDA, OfertaEstado.INVALIDA)
        for oferta in ofertas
    )


def validar_decision(session, emergencia, decision):
    if emergencia.estado != EmergenciaEstado.CONVOCATORIA_CERRADA:
        raise HTTPException(409, 'La emergencia no tiene una convocatoria cerrada pendiente de decisión.')

    lotes = lotes_pendientes(session, emergencia.id)
    ofertas = ofertas_vigentes(session, lotes)
    if not lotes or not validacion_completa(ofertas):
        raise HTTPException(409, 'Primero debe completarse la validación nacional de las ofertas.')
    ahora = datetime.now(timezone.utc)
    if any(utc(lote.fechaLimiteConvocatoria) >= ahora for lote in lotes):
        raise HTTPException(409, 'La convocatoria sigue abierta.')
    if resultado_guardado(session, emergencia.id)['cobertura_suficiente']:
        raise HTTPException(409, 'La emergencia tiene cobertura suficiente para adjudicar.')
    if decision.accion == 'parcial' and not lotes_con_recursos_verificados(ofertas):
        raise HTTPException(409, 'La emergencia no tiene recursos verificados para adjudicar.')
    elegibles = ({o.lote_id for o in ofertas if not o.valida}
                 if decision.accion == 'parcial' else lotes_con_faltante(lotes))
    if ((decision.accion != 'parcial' and not elegibles)
            or len(decision.lote_ids) != len(elegibles) or set(decision.lote_ids) != elegibles):
        raise HTTPException(422, 'La decisión debe incluir todos los lotes elegibles de la ronda actual.')

    cantidades = {lote.lote_id: lote.cantidad for lote in decision.lotes}
    if decision.accion == 'reformular':
        if len(cantidades) != len(decision.lotes) or set(cantidades) != elegibles:
            raise HTTPException(422, 'Debe indicar una cantidad para cada lote que se reformula.')
    elif cantidades:
        raise HTTPException(422, 'Solo se envían cantidades al reformular.')
    return [lote for lote in lotes if lote.id in elegibles], cantidades


def decision_ya_aplicada(session, emergencia, decision):
    if session.exec(select(Oferta.id).join(Lote).where(
        Lote.emergenciaId == emergencia.id, Oferta.tarea_bonita_descarte == decision.tarea_id,
        Oferta.descartada_en.is_not(None),
    )).first() is not None:
        return True
    if not decision.fecha_limite or not decision.lote_ids:
        return False

    # Los lotes sin ofertas no tienen filas de descarte que identifiquen el reintento.
    fecha_limite = utc(decision.fecha_limite)
    origen = Lote.id if decision.accion == 'reabrir' else Lote.loteOrigenId
    lotes = session.exec(select(origen, Lote.fechaLimiteConvocatoria).where(
        Lote.emergenciaId == emergencia.id, origen.in_(decision.lote_ids),
    )).all()
    aplicados = {lote_id for lote_id, limite in lotes if utc(limite) == fecha_limite}
    return aplicados == set(decision.lote_ids)


def abrir_nueva_convocatoria(session, emergencia, decision):
    if decision_ya_aplicada(session, emergencia, decision):
        return
    lotes, cantidades = validar_decision(session, emergencia, decision)
    fecha_limite = decision.fecha_limite or (
        datetime.now(timezone.utc) + timedelta(milliseconds=decision.ventana_ms)
    )
    for oferta in ofertas_vigentes(session, lotes):
        oferta.accion_tomada = decision.accion
        oferta.tarea_bonita_descarte = decision.tarea_id
        session.add(oferta)
    for lote in lotes:
        motivo = 'reapertura' if decision.accion == 'reabrir' else 'reformulacion'
        descartar_ofertas(session, lote, motivo)
        if decision.accion == 'reabrir':
            lote.estado = LoteEstado.CREADO
            lote.fechaLimiteConvocatoria = fecha_limite
        else:
            lote.estado = LoteEstado.REFORMULADO
            session.add(Lote(
                emergenciaId=emergencia.id, tipoRecurso=lote.tipoRecurso,
                descripcion=lote.descripcion, recurso_codigo=lote.recurso_codigo,
                cantidad=cantidades[lote.id], fechaLimiteConvocatoria=fecha_limite,
                loteOrigenId=lote.id,
            ))
        session.add(lote)
    emergencia.estado = EmergenciaEstado.PUBLICADA
    session.add(emergencia)
    session.commit()


def iniciar_adjudicacion(session, emergencia, parcial):
    if emergencia.estado in (EmergenciaEstado.EN_ADJUDICACION, EmergenciaEstado.ADJUDICADA,
                             EmergenciaEstado.MONITOREO_FINALIZADO):
        return
    if emergencia.estado != EmergenciaEstado.CONVOCATORIA_CERRADA:
        raise HTTPException(409, 'La convocatoria debe estar cerrada para adjudicar.')
    lotes = lotes_pendientes(session, emergencia.id)
    ofertas = ofertas_vigentes(session, lotes)
    if not lotes or not validacion_completa(ofertas):
        raise HTTPException(409, 'La validación nacional todavía no se completó.')
    if not parcial and not resultado_guardado(session, emergencia.id)['cobertura_suficiente']:
        raise HTTPException(409, 'La cobertura es insuficiente para adjudicar automáticamente.')
    adjudicables = {lote.id for lote in lotes}
    if parcial:
        adjudicables = lotes_con_recursos_verificados(ofertas)
        if not adjudicables:
            raise HTTPException(409, 'La emergencia no tiene recursos verificados para adjudicar.')
        for oferta in ofertas:
            if oferta.valida or oferta.lote_id not in adjudicables:
                continue
            resultado = oferta.resultado_validacion or {}
            participantes = [
                {**p, 'cantidad_aceptada': p['cantidad_verificada']}
                for p in resultado.get('participantes', [])
            ]
            oferta.resultado_validacion = {
                **resultado, 'participantes': participantes,
                'cantidad_aceptada': sum(p['cantidad_aceptada'] for p in participantes),
            }
            oferta.accion_tomada = 'parcial'
            session.add(oferta)
    ahora = datetime.now(timezone.utc)
    for lote in lotes:
        if utc(lote.fechaLimiteConvocatoria) > ahora:
            lote.fechaLimiteConvocatoria = ahora
        lote.estado = (LoteEstado.EN_ADJUDICACION if lote.id in adjudicables
                       else LoteEstado.CERRADO_SIN_ADJUDICACION)
        session.add(lote)
    emergencia.estado = EmergenciaEstado.EN_ADJUDICACION
    session.add(emergencia)
    session.commit()
