from datetime import datetime, timezone
import httpx
from sqlmodel import Session, select
from models.emergencia import Emergencia
from models.lote import Lote
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ConvocatoriaAbierta(ValueError):
    pass


async def evaluar_oferta(session, oferta, lote, nacional, bonita, cuits, inventarios):
    if not lote.recurso_codigo:
        raise ValueError('El lote no tiene vinculado un código de recurso nacional')
    participantes = session.exec(select(ParticipanteOferta).where(
        ParticipanteOferta.oferta_id == oferta.id,
        ParticipanteOferta.cantidad_aportada != None,
    ).order_by(ParticipanteOferta.id)).all()
    detalles = []
    aportes_por_cuit = {}
    for participante in participantes:
        if participante.ong_id not in cuits:
            cuits[participante.ong_id] = await bonita.obtener_cuit_ong(participante.ong_id)
        cuit = cuits[participante.ong_id]
        if not cuit:
            raise ValueError(f'El usuario de Bonita {participante.ong_id} no tiene cuitONG cargado')
        if cuit not in inventarios:
            inventarios[cuit] = await nacional.inventario(cuit)
        inventario = inventarios[cuit]
        recurso = next((r for r in (inventario or {}).get('recursos', [])
                        if r['codigo'] == lote.recurso_codigo), None)
        disponible, motivo = 0, None
        if not inventario:
            motivo = 'ONG no registrada en el Sistema Nacional'
        elif inventario['estado'] != 'HABILITADA':
            motivo = 'ONG no habilitada en el Sistema Nacional'
        elif recurso is None:
            motivo = 'La ONG no tiene registrado el recurso solicitado'
        else:
            disponible = max(0, recurso['cantidadTotal'] - recurso['cantidadComprometida'])
        # Representantes de una misma ONG comparten inventario dentro del consorcio.
        ya_ofertado = aportes_por_cuit.get(cuit, 0)
        cantidad = participante.cantidad_aportada
        aceptable = min(cantidad, max(0, disponible - ya_ofertado))
        aportes_por_cuit[cuit] = ya_ofertado + cantidad
        if aceptable < cantidad and motivo is None:
            motivo = 'Disponibilidad insuficiente para el aporte comprometido'
        detalles.append({
            'participante_id': participante.id, 'ong_id': participante.ong_id,
            'cuit': cuit, 'ong_nacional_id': inventario['id'] if inventario else None,
            'ong_nombre': inventario['razonSocial'] if inventario else None,
            'recurso_codigo': lote.recurso_codigo,
            'cantidad_ofertada': cantidad, 'cantidad_disponible': disponible,
            'cantidad_verificada': aceptable, 'faltante': cantidad - aceptable,
            'valida': motivo is None, 'motivo': motivo,
        })
    return {
        'valida': bool(detalles) and all(p['valida'] for p in detalles),
        'inventario_valido': bool(detalles) and all(p['valida'] for p in detalles),
        'motivo': None if detalles else 'La oferta no tiene aportes confirmados',
        'participantes': detalles,
        'cantidad_ofertada': sum(p['cantidad_ofertada'] for p in detalles),
        'cantidad_verificada': sum(p['cantidad_verificada'] for p in detalles),
    }


async def validar_emergencia(session, emergencia_id, nacional, bonita, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    emergencia = session.exec(select(Emergencia).where(Emergencia.id == emergencia_id)
                              .with_for_update(nowait=True)).first()
    if not emergencia:
        raise LookupError('Emergencia no encontrada')
    lotes = session.exec(select(Lote).where(
        Lote.emergenciaId == emergencia_id, Lote.estado != 'reformulado',
    )).all()
    if not lotes or any(utc(l.fechaLimiteConvocatoria) >= ahora for l in lotes):
        raise ConvocatoriaAbierta('La ventana de urgencia todavía está abierta')
    cuits, inventarios, resultados = {}, {}, []
    for lote in lotes:
        ofertas = session.exec(select(Oferta).where(Oferta.lote_id == lote.id)
                               .order_by(Oferta.id)).all()
        for oferta in ofertas:
            if oferta.accion_tomada:
                continue
            if (oferta.estado_validacion in ('valida', 'invalida') and oferta.ventana_validada
                    and utc(oferta.ventana_validada) == utc(lote.fechaLimiteConvocatoria)):
                resultados.append(oferta)
                continue
            try:
                resultado = await evaluar_oferta(session, oferta, lote, nacional, bonita, cuits, inventarios)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                oferta.estado_validacion = 'pendiente'
                oferta.resultado_validacion = {
                    'error': str(error) if isinstance(error, ValueError) else
                    'No se pudo consultar el inventario o la identidad. Hay que reintentar la validación.',
                    'intentada_en': ahora.isoformat(),
                }
                oferta.validada_en = None
            else:
                oferta.valida = resultado['valida']
                oferta.estado_validacion = 'valida' if oferta.valida else 'invalida'
                oferta.resultado_validacion = resultado
                oferta.validada_en = ahora
                oferta.ventana_validada = lote.fechaLimiteConvocatoria
            session.add(oferta)
            resultados.append(oferta)
        cobertura = sum(
            (o.resultado_validacion or {}).get('cantidad_verificada', 0)
            for o in ofertas if o.estado_validacion != 'pendiente'
            and (o.resultado_validacion or {}).get('inventario_valido', o.valida)
        )
        # La falta de cobertura también requiere una decisión del coordinador.
        if not any(o.estado_validacion == 'pendiente' for o in ofertas) and cobertura < lote.cantidad:
            for oferta in ofertas:
                if oferta.accion_tomada or not (oferta.resultado_validacion or {}).get('inventario_valido', oferta.valida):
                    continue
                resultado = dict(oferta.resultado_validacion or {})
                resultado.update({
                    'valida': False,
                    'motivo': f'Las ofertas con recursos suficientes cubren {cobertura} de {lote.cantidad} unidades del lote.',
                    'faltante_cobertura_lote': lote.cantidad - cobertura,
                })
                oferta.resultado_validacion = resultado
                oferta.estado_validacion = 'invalida'
                oferta.valida = False
                session.add(oferta)
        lote.cantidadCubierta = cobertura
        session.add(lote)
    session.commit()
    return resultados


