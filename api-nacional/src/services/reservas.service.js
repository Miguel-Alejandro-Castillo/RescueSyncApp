import { isDeepStrictEqual } from 'node:util';
import { validarEmergencia, comprobarSolicitud } from './validacion.service.js';
const conflict = message => Object.assign(new Error(message), { status: 409, code: 'RESERVATION_CONFLICT' });
const badRequest = message => Object.assign(new Error(message), { status: 400 });
const idValido = id => typeof id === 'string' && id.length > 0 && id.length <= 128;

// También serializa validaciones de emergencias distintas que comparten inventario.
async function bloquear(tx) {
  await tx.$queryRawUnsafe('SELECT pg_advisory_xact_lock(7284101)::text');
}

export async function reservarOfertas(prisma, solicitud) {
  comprobarSolicitud(solicitud);
  const ids = solicitud.lotes.map(lote => lote.reserva_id);
  if (ids.some(id => !idValido(id)) || new Set(ids).size !== ids.length) {
    throw badRequest('Cada lote debe identificar su reserva de convocatoria');
  }
  return prisma.$transaction(async tx => {
    await bloquear(tx);
    const existentes = await tx.reservaConvocatoria.findMany({ where: { id: { in: ids } } });
    const porId = new Map(existentes.map(reserva => [reserva.id, reserva]));
    const nuevos = [];
    for (const lote of solicitud.lotes) {
      const guardada = porId.get(lote.reserva_id);
      if (!guardada) {
        nuevos.push(lote);
      } else if (guardada.liberadaEn || !isDeepStrictEqual(guardada.solicitud, lote)) {
        throw conflict('La convocatoria ya fue liberada o su solicitud cambió');
      }
    }
    if (nuevos.length) {
      await reservarLotesNuevos(tx, nuevos, porId);
    }
    const resultados = solicitud.lotes.map(lote => porId.get(lote.reserva_id).resultado);
    return {
      resultados: resultados.flatMap(r => r.resultados),
      cobertura_por_lote: resultados.flatMap(r => r.cobertura_por_lote),
    };
  }, { timeout: 30000 });
}

async function reservarLotesNuevos(tx, lotes, porId) {
    const recursos = await tx.recurso.findMany({ include: { categoria: true } });
    const resultado = await validarEmergencia({ lotes }, cuits => tx.ong.findMany({
      where: { cuit: { in: cuits } }, include: { recursos: { include: { recurso: true } } },
    }), recursos);
    for (const [key, cantidad] of compromisos(resultado)) {
      const [ongId, recursoId] = key.split(':').map(Number);
      const updated = await tx.$executeRaw`UPDATE "OngRecurso" SET "cantidadReservada" = "cantidadReservada" + ${cantidad}
         WHERE "ongId" = ${ongId} AND "recursoId" = ${recursoId}
           AND "cantidadTotal" - "cantidadReservada" >= ${cantidad}`;
      if (updated !== 1) throw conflict('El inventario cambió durante la reserva');
    }
    for (const lote of lotes) {
      const registro = await tx.reservaConvocatoria.create({ data: {
        id: lote.reserva_id,
        solicitud: lote,
        resultado: {
          resultados: resultado.resultados.filter(o => o.lote_id === lote.lote_id)
            .map(o => ({ ...o, reserva_id: lote.reserva_id })),
          cobertura_por_lote: resultado.cobertura_por_lote.filter(c => c.lote_id === lote.lote_id),
        },
      } });
      porId.set(registro.id, registro);
    }
}

function compromisos(resultado) {
  const cantidades = new Map();
  for (const o of resultado.resultados) for (const p of o.resultado_validacion.participantes || []) {
    if (!p.cantidad_verificada) continue;
    const key = p.ong_nacional_id + ':' + p.recurso_nacional_id;
    cantidades.set(key, (cantidades.get(key) || 0) + p.cantidad_verificada);
  }
  return cantidades;
}

export async function liberarReserva(prisma, reserva) {
  if (!idValido(reserva?.reserva_id) || !Array.isArray(reserva.resultados)) {
    throw badRequest('Detalle de recursos a liberar inválido');
  }
  return prisma.$transaction(async tx => {
    await bloquear(tx);
    const id = reserva.reserva_id;
    const guardada = await tx.reservaConvocatoria.findUnique({ where: { id } });
    if (guardada?.liberadaEn) return { liberada: true };
    if (!guardada && reserva.legado !== true) throw conflict('No existe la reserva de la convocatoria');
    const resultado = guardada?.resultado ?? { resultados: reserva.resultados };
    for (const o of resultado.resultados) {
      if (!Array.isArray(o?.resultado_validacion?.participantes)) throw badRequest('Participantes inválidos');
      for (const p of o.resultado_validacion.participantes) {
        if (!Number.isSafeInteger(p?.cantidad_verificada) || p.cantidad_verificada < 0 ||
            (p.cantidad_verificada > 0 && (!Number.isSafeInteger(p.ong_nacional_id) || !Number.isSafeInteger(p.recurso_nacional_id)))) {
          throw badRequest('Cantidades o recursos inválidos');
        }
      }
    }
    for (const [key, cantidad] of compromisos(resultado)) {
      const [ongId, recursoId] = key.split(':').map(Number);
      const updated = await tx.ongRecurso.updateMany({
        where: { ongId, recursoId, cantidadReservada: { gte: cantidad } },
        data: { cantidadReservada: { decrement: cantidad } },
      });
      if (updated.count !== 1) throw conflict('Inventario inconsistente al liberar recursos');
    }
    const liberadaEn = new Date();
    if (guardada) {
      await tx.reservaConvocatoria.update({ where: { id }, data: { liberadaEn } });
    } else {
      await tx.reservaConvocatoria.create({ data: { id, resultado, liberadaEn } });
    }
    return { liberada: true };
  }, { timeout: 30000 });
}
