"""Preparar aportes y persistir la validación calculada por la API Nacional."""
from datetime import datetime, timezone
import httpx
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


async def validar_emergencia(session, emergencia_id, nacional, ahora=None, *, commit=True):
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
    ofertas_por_id = {}
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote.id).order_by(Oferta.id)).all()
        datos_lote = {'lote_id': lote.id, 'recurso_nombre': lote.descripcion,
                      'cantidad_requerida': lote.cantidad, 'ofertas': []}
        for oferta in ofertas:
            participantes = session.exec(select(ParticipanteOferta).where(
                ParticipanteOferta.oferta_id == oferta.id,
                ParticipanteOferta.cantidad_aportada != None,
            ).order_by(ParticipanteOferta.id)).all()
            datos = {'oferta_id': oferta.id, 'participantes': [
                {'participante_id': p.id, 'ong_id': p.ong_id, 'cuit': p.ong_cuit,
                 'cantidad_ofertada': p.cantidad_aportada} for p in participantes]}
            aceptada = (oferta.resultado_validacion or {}).get('cantidad_aceptada')
            if oferta.accion_tomada == 'parcial' and aceptada is not None:
                datos['cantidad_aceptada'] = aceptada
            datos_lote['ofertas'].append(datos)
            ofertas_por_id[oferta.id] = oferta
        solicitud['lotes'].append(datos_lote)
    try:
        respuesta = await nacional.validar_ofertas(solicitud)
        comprobar_respuesta(respuesta, solicitud)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        # Un fallo de consulta no representa una decisión de cobertura insuficiente.
        for oferta in ofertas_por_id.values():
            anterior = oferta.resultado_validacion or {}
            oferta.estado_validacion = 'pendiente'
            oferta.resultado_validacion = {
                'error': 'No se pudo completar la validación en el Sistema Nacional. Hay que reintentar.',
                'intentada_en': ahora.isoformat(),
                **({'cantidad_aceptada': anterior['cantidad_aceptada']}
                   if 'cantidad_aceptada' in anterior else {}),
            }
            oferta.validada_en = None
            oferta.ventana_validada = None
            session.add(oferta)
        if commit:
            session.commit()
            for oferta in ofertas_por_id.values():
                session.refresh(oferta)
        return {'emergencia_id': emergencia_id, 'completa': False, 'cobertura_suficiente': False,
                'cobertura_por_lote': [], 'ofertas_validas': 0, 'ofertas_invalidas': 0,
                'ofertas_pendientes': len(ofertas_por_id), 'resultados': list(ofertas_por_id.values())}
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
        session.add(lote)
    if commit:
        session.commit()
        for oferta in ofertas_por_id.values():
            session.refresh(oferta)
    return {**respuesta, 'resultados': list(ofertas_por_id.values())}
