import { validarEmergencia, comprobarSolicitud } from './validacion.service.js';
const conflict = message => Object.assign(new Error(message), { status: 409, code: 'RESERVATION_CONFLICT' });

// También serializa validaciones de emergencias distintas que comparten inventario.
async function bloquear(tx) {
  await tx.$queryRawUnsafe('SELECT pg_advisory_xact_lock(7284101)::text');
}

export async function reservarOfertas(prisma, solicitud) {
  comprobarSolicitud(solicitud);
  return prisma.$transaction(async tx => {
    await bloquear(tx);
    const recursos = await tx.recurso.findMany({ include: { categoria: true } });
    const resultado = await validarEmergencia(solicitud, cuits => tx.ong.findMany({
      where: { cuit: { in: cuits } }, include: { recursos: { include: { recurso: true } } },
    }), recursos);
    // Una vinculación pendiente no debe dejar compromisos parciales ocultos.
    if (!resultado.completa) return resultado;
    for (const [key, cantidad] of compromisos(resultado)) {
      const [ongId, recursoId] = key.split(':').map(Number);
      const updated = await tx.$executeRaw`UPDATE "OngRecurso" SET "cantidadReservada" = "cantidadReservada" + ${cantidad}
         WHERE "ongId" = ${ongId} AND "recursoId" = ${recursoId}
           AND "cantidadTotal" - "cantidadReservada" >= ${cantidad}`;
      if (updated !== 1) throw conflict('El inventario cambió durante la reserva');
    }
    return resultado;
  }, { timeout: 30000 });
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
  if (!reserva || !Array.isArray(reserva.resultados))
    throw Object.assign(new Error('Detalle de recursos a liberar inválido'), { status: 400 });
  for (const o of reserva.resultados) {
    if (!Array.isArray(o?.resultado_validacion?.participantes))
      throw Object.assign(new Error('Participantes inválidos'), { status: 400 });
    for (const p of o.resultado_validacion.participantes) {
      if (!Number.isSafeInteger(p.cantidad_verificada) || p.cantidad_verificada < 0 ||
          (p.cantidad_verificada > 0 && (!Number.isSafeInteger(p.ong_nacional_id) || !Number.isSafeInteger(p.recurso_nacional_id))))
        throw Object.assign(new Error('Cantidades o recursos inválidos'), { status: 400 });
    }
  }
  return prisma.$transaction(async tx => {
    await bloquear(tx);
    for (const [key, cantidad] of compromisos(reserva)) {
      const [ongId, recursoId] = key.split(':').map(Number);
      const updated = await tx.ongRecurso.updateMany({
        where: { ongId, recursoId, cantidadReservada: { gte: cantidad } },
        data: { cantidadReservada: { decrement: cantidad } },
      });
      if (updated.count !== 1) throw conflict('Inventario inconsistente al liberar recursos');
    }
    return { liberada: true };
  });
}
