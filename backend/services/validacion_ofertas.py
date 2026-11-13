"""Preparar aportes y persistir la validación calculada por la API Nacional."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from sqlmodel import select
from models.emergencia import Emergencia
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def identificador_reserva(emergencia, lote, ventana):
    return f'{emergencia.bonitaCaseId}:{lote.id}:{utc(ventana).isoformat()}'


def bloquear_decisiones(session, emergencia_id, oferta_id=None):
    try:
        session.exec(select(Emergencia.id).where(Emergencia.id == emergencia_id)
                     .with_for_update(nowait=True)).one()
    except OperationalError as error:
        raise HTTPException(409, 'Ya hay una operación en curso para esta emergencia.') from error
    pendiente = select(Oferta.id).join(Lote).where(
        Lote.emergenciaId == emergencia_id,
        Oferta.descartada_en.is_(None),
        Oferta.tarea_bonita_descarte.is_not(None),
    )
    if oferta_id is not None:
        pendiente = pendiente.where(Oferta.id != oferta_id)
    if session.exec(pendiente).first():
        raise HTTPException(409, 'Hay otro descarte pendiente para esta emergencia.')


class ConvocatoriaAbierta(ValueError):
    pass


def comprobar_respuesta(data, solicitud):
    """Comprobar el contrato remoto antes de guardar; no recalcular sus decisiones."""
    if not isinstance(data, dict):
        raise ValueError('Respuesta de validación nacional inválida')
    esperadas = {o['oferta_id']: l['lote_id'] for l in solicitud['lotes'] for o in l['ofertas']}
    reservas = {l['lote_id']: l['reserva_id'] for l in solicitud['lotes']}
    resultados = data.get('resultados')
    cobertura = data.get('cobertura_por_lote')
    if not isinstance(resultados, list) or not isinstance(cobertura, list):
        raise ValueError('La respuesta nacional está incompleta')
    if any(not isinstance(item, dict) for item in resultados + cobertura):
        raise ValueError('La respuesta nacional contiene resultados inválidos')
    if (len(resultados) != len(esperadas)
            or {o.get('oferta_id') for o in resultados} != set(esperadas)
            or len(cobertura) != len(solicitud['lotes'])
            or {l.get('lote_id') for l in cobertura} != {l['lote_id'] for l in solicitud['lotes']}):
        raise ValueError('La respuesta nacional no corresponde a los lotes y ofertas enviados')
    for o in resultados:
        r = o.get('resultado_validacion')
        if (o.get('lote_id') != esperadas[o['oferta_id']] or not isinstance(r, dict)
                or o.get('reserva_id') != reservas[o['lote_id']]
                or o.get('estado_validacion') not in ('valida', 'invalida')):
            raise ValueError('Resultado de oferta nacional inválido')
        if not isinstance(r.get('participantes'), list):
            raise ValueError('Resultado nacional sin detalle de los aportes')
        for participante in r['participantes']:
            cantidad = participante.get('cantidad_verificada') if isinstance(participante, dict) else None
            if type(cantidad) is not int or cantidad < 0:
                raise ValueError('Cantidad verificada de participante inválida')
    for l in cobertura:
        if (type(l.get('ofertado_valido')) is not int or l['ofertado_valido'] < 0
                or type(l.get('cubierto')) is not bool):
            raise ValueError('Cobertura nacional inválida')


def preparar_solicitud(session, emergencia_id, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    emergencia = session.exec(select(Emergencia).where(Emergencia.id == emergencia_id)
                              .with_for_update(nowait=True)).first()
    if not emergencia:
        raise LookupError('Emergencia no encontrada')
    lotes = session.exec(select(Lote).where(
        Lote.emergenciaId == emergencia_id, Lote.estado != LoteEstado.REFORMULADO,
    ).order_by(Lote.id)).all()
    if not lotes or any(utc(l.fechaLimiteConvocatoria) >= ahora for l in lotes):
        raise ConvocatoriaAbierta('La ventana de urgencia todavía está abierta')
    solicitud = {'lotes': []}
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(
            Oferta.lote_id == lote.id, Oferta.descartada_en.is_(None),
        ).order_by(Oferta.id)).all()
        if any(o.tarea_bonita_descarte for o in ofertas):
            raise ConvocatoriaAbierta('Hay un descarte de ofertas pendiente')
        if ofertas and all(o.validada_en is not None and o.ventana_validada is not None
                           and utc(o.ventana_validada) == utc(lote.fechaLimiteConvocatoria)
                           and o.estado_validacion in ('valida', 'invalida') for o in ofertas):
            continue
        datos_lote = {'lote_id': lote.id,
                      'reserva_id': identificador_reserva(emergencia, lote, lote.fechaLimiteConvocatoria),
                      'recurso_nombre': lote.descripcion, 'tipo_recurso': lote.tipoRecurso,
                      'cantidad_requerida': lote.cantidad, 'ofertas': []}
        for oferta in ofertas:
            participantes = session.exec(select(ParticipanteOferta).where(
                ParticipanteOferta.oferta_id == oferta.id,
                ParticipanteOferta.cantidad_aportada != None,
            ).order_by(ParticipanteOferta.id)).all()
            datos_lote['ofertas'].append({'oferta_id': oferta.id, 'participantes': [
                {'participante_id': p.id, 'cuit': p.ong_cuit,
                 'cantidad_ofertada': p.cantidad_aportada} for p in participantes]})
        solicitud['lotes'].append(datos_lote)
    if not solicitud['lotes']:
        solicitud['ya_validada'] = True
        solicitud['respuesta_guardada'] = resultado_guardado(session, emergencia_id)
    return solicitud


def resultado_guardado(session, emergencia_id):
    lotes = session.exec(select(Lote).where(Lote.emergenciaId == emergencia_id, Lote.estado != LoteEstado.REFORMULADO)).all()
    ofertas = session.exec(select(Oferta).where(
        Oferta.lote_id.in_([l.id for l in lotes]), Oferta.descartada_en.is_(None),
    )).all()
    validacion_completa = all(
        o.validada_en is not None and o.estado_validacion in ('valida', 'invalida')
        for o in ofertas
    )
    return dict(cobertura_suficiente=validacion_completa and all(l.cantidadCubierta >= l.cantidad for l in lotes))


def obtener_reservas_no_adjudicadas(session, emergencia_id):
    """Calcula el remanente reservado después de las adjudicaciones."""
    lotes = session.exec(select(Lote).where(Lote.emergenciaId == emergencia_id)).all()
    lote_ids = [lote.id for lote in lotes if lote.id is not None]
    respuesta_vacia = {"emergencia_id": emergencia_id, "data": [], "ofertas": []}
    if not lote_ids:
        return respuesta_vacia

    ofertas = session.exec(select(Oferta).where(
        Oferta.lote_id.in_(lote_ids),
        Oferta.resultado_validacion.is_not(None),
    ).order_by(Oferta.lote_id, Oferta.id)).all()
    if not ofertas:
        return respuesta_vacia

    detalles = session.exec(
        select(AdjudicacionDetalle, ParticipanteOferta)
        .join(
            ParticipanteOferta,
            AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id,
        )
        .join(
            Adjudicacion,
            AdjudicacionDetalle.adjudicacion_id == Adjudicacion.id,
        )
        .join(Lote, Adjudicacion.lote_id == Lote.id)
        .where(Lote.emergenciaId == emergencia_id)
    ).all()
    adjudicado_por_participante = {}
    for detalle, participante in detalles:
        adjudicado_por_participante[participante.id] = (
            adjudicado_por_participante.get(participante.id, 0)
            + detalle.cantidad_adjudicada
        )

    lotes_por_id = {lote.id: lote for lote in lotes}
    data_por_recurso = {}
    ofertas_resultado = []

    for oferta in ofertas:
        lote = lotes_por_id[oferta.lote_id]
        resultado = oferta.resultado_validacion or {}
        participantes_restantes = []

        for participante in resultado.get("participantes", []):
            participante_id = participante.get("participante_id")
            cantidad_reservada = participante.get("cantidad_verificada", 0)
            if (
                not isinstance(participante_id, int)
                or not isinstance(cantidad_reservada, int)
            ):
                raise ValueError(f"Resultado inválido para la oferta {oferta.id}")

            cantidad_adjudicada = adjudicado_por_participante.get(participante_id, 0)
            cantidad_a_liberar = cantidad_reservada - cantidad_adjudicada
            if cantidad_a_liberar < 0:
                raise ValueError(
                    f"La cantidad adjudicada excede la reservada para el participante "
                    f"{participante_id}"
                )
            if not cantidad_a_liberar:
                continue

            cuit = participante.get("cuit")
            if not isinstance(cuit, str) or not cuit.strip():
                raise ValueError(
                    f"El participante {participante_id} no tiene CUIT para liberar"
                )

            participantes_restantes.append({
                **participante,
                "cantidad_reservada": cantidad_reservada,
                "cantidad_adjudicada": cantidad_adjudicada,
                "cantidad_a_liberar": cantidad_a_liberar,
            })
            clave = (cuit.strip(), lote.descripcion)
            data_por_recurso[clave] = (
                data_por_recurso.get(clave, 0) + cantidad_a_liberar
            )

        if participantes_restantes:
            ofertas_resultado.append({
                "oferta_id": oferta.id,
                "lote_id": lote.id,
                "descripcion": lote.descripcion,
                "participantes": participantes_restantes,
            })

    data = [
        {
            "cuit": cuit,
            "descripcion": descripcion,
            "cantidad_a_liberar": cantidad,
        }
        for (cuit, descripcion), cantidad in sorted(data_por_recurso.items())
    ]
    return {
        "emergencia_id": emergencia_id,
        "data": data,
        "ofertas": ofertas_resultado,
    }


def guardar_resultado(session, emergencia_id, respuesta):
    ahora = datetime.now(timezone.utc)
    solicitud = preparar_solicitud(session, emergencia_id, ahora)
    if solicitud.get('ya_validada'):
        return solicitud['respuesta_guardada']
    comprobar_respuesta(respuesta, solicitud)
    lotes = session.exec(select(Lote).where(Lote.id.in_([l['lote_id'] for l in solicitud['lotes']]))).all()
    ofertas_por_id = {o.id: o for o in session.exec(select(Oferta).where(
        Oferta.lote_id.in_([l.id for l in lotes]), Oferta.descartada_en.is_(None),
    )).all()}
    lotes_por_id = {l.id: l for l in lotes}
    cobertura_por_id = {l['lote_id']: l for l in respuesta['cobertura_por_lote']}
    for item in respuesta['resultados']:
        oferta = ofertas_por_id[item['oferta_id']]
        resultado = dict(item['resultado_validacion'])
        resultado['reserva_id'] = item['reserva_id']
        oferta.resultado_validacion = resultado
        oferta.estado_validacion = item['estado_validacion']
        oferta.valida = item['estado_validacion'] == 'valida'
        oferta.validada_en = ahora
        oferta.ventana_validada = lotes_por_id[item['lote_id']].fechaLimiteConvocatoria
        session.add(oferta)
    for lote in lotes:
        lote.cantidadCubierta = cobertura_por_id[lote.id]['ofertado_valido']
        codigo = cobertura_por_id[lote.id].get('recurso_codigo')
        if codigo:
            lote.recurso_codigo = codigo
        session.add(lote)
    session.commit()
    for oferta in ofertas_por_id.values():
        session.refresh(oferta)
    return resultado_guardado(session, emergencia_id)


def descartar_ofertas(session, lote, motivo):
    lote.cantidadCubierta = 0
    session.add(lote)
    ahora = datetime.now(timezone.utc)
    for oferta in session.exec(select(Oferta).where(
        Oferta.lote_id == lote.id, Oferta.descartada_en.is_(None),
    )).all():
        oferta.descartada_en = ahora
        oferta.motivo_descarte = motivo
        session.add(oferta)
