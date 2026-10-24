"""Preparar aportes y persistir la validación calculada por la API Nacional."""
from datetime import datetime, timezone
from sqlmodel import select
from models.emergencia import Emergencia
from models.lote import Lote
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ConvocatoriaAbierta(ValueError):
    pass


def comprobar_respuesta(data, solicitud):
    """Comprobar el contrato remoto antes de guardar; no recalcular sus decisiones."""
    if not isinstance(data, dict):
        raise ValueError('Respuesta de validación nacional inválida')
    esperadas = {o['oferta_id']: l['lote_id'] for l in solicitud['lotes'] for o in l['ofertas']}
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
        Lote.emergenciaId == emergencia_id, Lote.estado != 'reformulado',
    ).order_by(Lote.id)).all()
    if not lotes or any(utc(l.fechaLimiteConvocatoria) >= ahora for l in lotes):
        raise ConvocatoriaAbierta('La ventana de urgencia todavía está abierta')
    solicitud = {'lotes': []}
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote.id).order_by(Oferta.id)).all()
        if ofertas and all(o.validada_en is not None and o.ventana_validada is not None
                           and utc(o.ventana_validada) == utc(lote.fechaLimiteConvocatoria)
                           and o.estado_validacion in ('valida', 'invalida') for o in ofertas):
            continue
        datos_lote = {'lote_id': lote.id,
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
    lotes = session.exec(select(Lote).where(Lote.emergenciaId == emergencia_id, Lote.estado != 'reformulado')).all()
    ofertas = session.exec(select(Oferta).where(Oferta.lote_id.in_([l.id for l in lotes]))).all()
    validacion_completa = all(
        o.validada_en is not None and o.estado_validacion in ('valida', 'invalida')
        for o in ofertas
    )
    return dict(cobertura_suficiente=validacion_completa and all(l.cantidadCubierta >= l.cantidad for l in lotes))


def guardar_resultado(session, emergencia_id, respuesta):
    ahora = datetime.now(timezone.utc)
    solicitud = preparar_solicitud(session, emergencia_id, ahora)
    if solicitud.get('ya_validada'):
        return solicitud['respuesta_guardada']
    comprobar_respuesta(respuesta, solicitud)
    lotes = session.exec(select(Lote).where(Lote.id.in_([l['lote_id'] for l in solicitud['lotes']]))).all()
    ofertas_por_id = {o.id: o for o in session.exec(select(Oferta).where(Oferta.lote_id.in_([l.id for l in lotes]))).all()}
    lotes_por_id = {l.id: l for l in lotes}
    cobertura_por_id = {l['lote_id']: l for l in respuesta['cobertura_por_lote']}
    for item in respuesta['resultados']:
        oferta = ofertas_por_id[item['oferta_id']]
        resultado = dict(item['resultado_validacion'])
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


def reiniciar_validacion(session, lote_id):
    lote = session.get(Lote, lote_id)
    lote.cantidadCubierta = 0
    session.add(lote)
    for oferta in session.exec(select(Oferta).where(Oferta.lote_id == lote.id)).all():
        oferta.valida = True
        oferta.estado_validacion = 'pendiente'
        oferta.validada_en = None
        oferta.ventana_validada = None
        oferta.resultado_validacion = None
        oferta.accion_tomada = None
        session.add(oferta)
