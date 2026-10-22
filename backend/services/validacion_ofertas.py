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
    if not isinstance(data, dict) or data.get('emergencia_id') != solicitud['emergencia_id']:
        raise ValueError('Respuesta de validación nacional inválida')
    if any(type(data.get(key)) is not bool for key in ('completa', 'cobertura_suficiente')):
        raise ValueError('La respuesta nacional no contiene los indicadores de cobertura')
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
                or o.get('estado_validacion') not in ('pendiente', 'valida', 'invalida')):
            raise ValueError('Resultado de oferta nacional inválido')
        if o['estado_validacion'] == 'pendiente':
            if not isinstance(r.get('error'), str):
                raise ValueError('Resultado pendiente sin motivo')
        elif type(r.get('valida')) is not bool or not isinstance(r.get('participantes'), list):
            raise ValueError('Resultado nacional sin detalle de los aportes')
    for l in cobertura:
        if (type(l.get('ofertado_valido')) is not int or l['ofertado_valido'] < 0
                or type(l.get('cantidad_ofertada')) is not int or l['cantidad_ofertada'] < 0
                or type(l.get('faltante')) is not int or l['faltante'] < 0
                or type(l.get('cubierto')) is not bool or type(l.get('completa')) is not bool):
            raise ValueError('Cobertura nacional inválida')
    if any(type(data.get(k)) is not int or data[k] < 0
           for k in ('ofertas_validas', 'ofertas_invalidas', 'ofertas_pendientes')):
        raise ValueError('La respuesta nacional no contiene los conteos de ofertas')


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
    solicitud = {'emergencia_id': emergencia_id, 'lotes': []}
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote.id).order_by(Oferta.id)).all()
        if ofertas and all(o.validada_en is not None and o.ventana_validada is not None
                           and utc(o.ventana_validada) == utc(lote.fechaLimiteConvocatoria)
                           and o.estado_validacion in ('valida', 'invalida') for o in ofertas):
            continue
        datos_lote = {'lote_id': lote.id, 'ventana_validada': utc(lote.fechaLimiteConvocatoria).isoformat(),
                      'recurso_nombre': lote.descripcion, 'tipo_recurso': lote.tipoRecurso,
                      'cantidad_requerida': lote.cantidad, 'ofertas': []}
        for oferta in ofertas:
            participantes = session.exec(select(ParticipanteOferta).where(
                ParticipanteOferta.oferta_id == oferta.id,
                ParticipanteOferta.cantidad_aportada != None,
            ).order_by(ParticipanteOferta.id)).all()
            datos_lote['ofertas'].append({'oferta_id': oferta.id, 'participantes': [
                {'participante_id': p.id, 'ong_id': p.ong_id, 'cuit': p.ong_cuit,
                 'cantidad_ofertada': p.cantidad_aportada} for p in participantes]})
        solicitud['lotes'].append(datos_lote)
    if not solicitud['lotes']:
        solicitud['ya_validada'] = True
        solicitud['respuesta_guardada'] = resultado_guardado(session, emergencia_id)
    return solicitud


def resultado_guardado(session, emergencia_id):
    lotes = session.exec(select(Lote).where(Lote.emergenciaId == emergencia_id, Lote.estado != 'reformulado')).all()
    ofertas = session.exec(select(Oferta).where(Oferta.lote_id.in_([l.id for l in lotes]))).all()
    cobertura = []
    for lote in lotes:
        ofertas_lote = [o for o in ofertas if o.lote_id == lote.id]
        guardada = next(((o.resultado_validacion or {}).get('cobertura_lote') for o in ofertas_lote
                         if (o.resultado_validacion or {}).get('cobertura_lote')), None)
        cobertura.append(guardada or dict(lote_id=lote.id, requerido=lote.cantidad, cantidad_ofertada=0,
                                          ofertado_valido=0, faltante=lote.cantidad, completa=not ofertas_lote, cubierto=False))
    pendientes = sum(o.estado_validacion == 'pendiente' for o in ofertas)
    return dict(emergencia_id=emergencia_id, completa=pendientes == 0,
                cobertura_suficiente=pendientes == 0 and all(c['cubierto'] for c in cobertura),
                cobertura_por_lote=cobertura,
                ofertas_validas=sum(o.estado_validacion == 'valida' for o in ofertas),
                ofertas_invalidas=sum(o.estado_validacion == 'invalida' for o in ofertas), ofertas_pendientes=pendientes,
                resultados=[dict(oferta_id=o.id, lote_id=o.lote_id, estado_validacion=o.estado_validacion,
                                 resultado_validacion=o.resultado_validacion) for o in ofertas])


def guardar_resultado(session, emergencia_id, respuesta):
    ahora = datetime.now(timezone.utc)
    solicitud = preparar_solicitud(session, emergencia_id, ahora)
    if solicitud.get('ya_validada'):
        return solicitud['respuesta_guardada']
    comprobar_respuesta(respuesta, solicitud)
    if not respuesta['completa']:
        raise ValueError('La validación está incompleta')
    ventanas = {l['lote_id']: l['ventana_validada'] for l in solicitud['lotes']}
    if any(l.get('ventana_validada') != ventanas[l['lote_id']] for l in respuesta['cobertura_por_lote']):
        raise ValueError('La respuesta no corresponde a la ventana de la convocatoria actual')
    lotes = session.exec(select(Lote).where(Lote.id.in_([l['lote_id'] for l in solicitud['lotes']]))).all()
    ofertas_por_id = {o.id: o for o in session.exec(select(Oferta).where(Oferta.lote_id.in_([l.id for l in lotes]))).all()}
    lotes_por_id = {l.id: l for l in lotes}
    cobertura_por_id = {l['lote_id']: l for l in respuesta['cobertura_por_lote']}
    for item in respuesta['resultados']:
        oferta = ofertas_por_id[item['oferta_id']]
        resultado = dict(item['resultado_validacion'])
        resultado['origen'] = 'sistema_nacional'
        resultado['cobertura_lote'] = cobertura_por_id[item['lote_id']]
        oferta.resultado_validacion = resultado
        oferta.estado_validacion = item['estado_validacion']
        if item['estado_validacion'] == 'pendiente':
            oferta.validada_en = None
            oferta.ventana_validada = None
        else:
            oferta.valida = resultado['valida']
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
