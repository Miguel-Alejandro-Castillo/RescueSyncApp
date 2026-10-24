/** Validación sobre el inventario disponible de esta transacción. */
export function comprobarSolicitud(data) {
  const fail = () => { throw Object.assign(new Error('Lotes, ofertas o participantes inválidos'), { status: 400, code: 'INVALID_VALIDATION_REQUEST' }); };
  const id = value => Number.isSafeInteger(value) && value > 0;
  const cantidad = value => Number.isSafeInteger(value) && value >= 0;
  if (!data || !Array.isArray(data.lotes) || !data.lotes.length) fail();
  const lotes = new Set(), ofertas = new Set(), participantes = new Set();
  for (const lote of data.lotes) {
    if (!id(lote.lote_id) || lotes.has(lote.lote_id) || !cantidad(lote.cantidad_requerida) || lote.cantidad_requerida === 0 || !Array.isArray(lote.ofertas)) fail();
    for (const campo of ['recurso_nombre', 'tipo_recurso']) {
      if (typeof lote[campo] !== 'string' || !lote[campo].trim() || lote[campo].length > 255) fail();
    }
    lotes.add(lote.lote_id);
    for (const oferta of lote.ofertas) {
      if (!id(oferta.oferta_id) || ofertas.has(oferta.oferta_id) || !Array.isArray(oferta.participantes)) fail();
      if (oferta.cantidad_aceptada != null && !cantidad(oferta.cantidad_aceptada)) fail();
      ofertas.add(oferta.oferta_id);
      for (const p of oferta.participantes) {
        if (!id(p.participante_id) || !id(p.ong_id) || participantes.has(p.participante_id) || !cantidad(p.cantidad_ofertada)) fail();
        if (typeof p.cuit !== 'string' || !p.cuit.trim() || p.cuit.length > 32) fail();
        participantes.add(p.participante_id);
      }
    }
  }
}

function resolverLote(lote, recursos) {
  const recurso = recursos.find(r => r.nombre === lote.recurso_nombre && r.categoria.nombre === lote.tipo_recurso);
  return { ...lote, recurso_codigo: recurso?.codigo ?? null };
}

function evaluarOferta(oferta, lote, inventarios) {
  const aportes = new Map();
  const participantes = oferta.participantes.map(p => {
    const cuit = p.cuit.trim();
    const ong = inventarios.get(cuit);
    const recurso = ong?.recursos.find(r => r.recurso.codigo === lote.recurso_codigo);
    const disponible = ong?.estado === 'HABILITADA' && recurso
      ? Math.max(0, recurso.cantidadTotal - recurso.cantidadReservada)
      : 0;
    const previo = aportes.get(cuit) || 0;
    const verificada = Math.min(p.cantidad_ofertada, Math.max(0, disponible - previo));
    aportes.set(cuit, previo + p.cantidad_ofertada);
    return { participante_id: p.participante_id, ong_id: p.ong_id, cuit,
      ong_nacional_id: ong?.id ?? null, ong_nombre: ong?.razonSocial ?? null,
      recurso_nacional_id: recurso?.recursoId ?? null, recurso_codigo: lote.recurso_codigo, cantidad_ofertada: p.cantidad_ofertada,
      cantidad_verificada: verificada };
  });
  const cantidadVerificada = participantes.reduce((n, p) => n + p.cantidad_verificada, 0);
  const valida = participantes.length > 0 && cantidadVerificada >= lote.cantidad_requerida;
  const resultado = { valida, inventario_valido: valida, participantes,
    motivo: valida ? null : `La oferta conjunta cubre ${cantidadVerificada} de ${lote.cantidad_requerida} unidades requeridas.`,
    cantidad_ofertada: participantes.reduce((n, p) => n + p.cantidad_ofertada, 0),
    cantidad_verificada: cantidadVerificada };
  if (oferta.cantidad_aceptada != null) {
    resultado.cantidad_aceptada = Math.min(oferta.cantidad_aceptada, resultado.cantidad_verificada);
    let restante = resultado.cantidad_aceptada;
    for (const p of participantes) {
      p.cantidad_aceptada = Math.min(restante, p.cantidad_verificada);
      restante -= p.cantidad_aceptada;
    }
  }
  return resultado;
}

export async function validarEmergencia(data, consultarInventarios, recursos = []) {
  comprobarSolicitud(data);
  const cuits = [...new Set(data.lotes.flatMap(l => l.ofertas.flatMap(o => o.participantes.map(p => p.cuit?.trim()).filter(Boolean))))];
  const inventarios = new Map((cuits.length ? await consultarInventarios(cuits) : []).map(o => [o.cuit, o]));
  const resultados = [], cobertura_por_lote = [];
  for (const lote of data.lotes.map(l => resolverLote(l, recursos))) {
    const ofertas = lote.ofertas.map(o => {
      const resultado = evaluarOferta(o, lote, inventarios);
      for (const p of resultado.participantes) {
        const recurso = inventarios.get(p.cuit)?.recursos.find(r => r.recurso.codigo === lote.recurso_codigo);
        if (recurso) recurso.cantidadReservada += p.cantidad_verificada;
      }
      return { oferta_id: o.oferta_id, lote_id: lote.lote_id,
        estado_validacion: resultado.valida ? 'valida' : 'invalida',
        resultado_validacion: resultado };
    });
    const ofertado_valido = ofertas.reduce((n, o) => {
      const r = o.resultado_validacion;
      return n + (r.cantidad_aceptada ?? (r.inventario_valido ? r.cantidad_verificada : 0));
    }, 0);
    const cobertura = { lote_id: lote.lote_id, ventana_validada: lote.ventana_validada, recurso_codigo: lote.recurso_codigo ?? null, requerido: lote.cantidad_requerida,
      cantidad_ofertada: lote.ofertas.reduce((n, o) => n + o.participantes.reduce((m, p) => m + p.cantidad_ofertada, 0), 0),
      ofertado_valido, faltante: Math.max(0, lote.cantidad_requerida - ofertado_valido),
      cubierto: ofertado_valido >= lote.cantidad_requerida };
    resultados.push(...ofertas);
    cobertura_por_lote.push(cobertura);
  }
  return {
    cobertura_por_lote: cobertura_por_lote.map(l => ({
      lote_id: l.lote_id,
      ventana_validada: l.ventana_validada,
      recurso_codigo: l.recurso_codigo,
      ofertado_valido: l.ofertado_valido,
      cubierto: l.cubierto,
    })),
    resultados: resultados.map(o => ({
      oferta_id: o.oferta_id,
      lote_id: o.lote_id,
      estado_validacion: o.estado_validacion,
      resultado_validacion: {
        motivo: o.resultado_validacion.motivo,
        participantes: o.resultado_validacion.participantes.map(p => ({
          participante_id: p.participante_id,
          ong_nombre: p.ong_nombre,
          ong_nacional_id: p.ong_nacional_id,
          recurso_nacional_id: p.recurso_nacional_id,
          cantidad_ofertada: p.cantidad_ofertada,
          cantidad_verificada: p.cantidad_verificada,
        })),
      },
    })),
  };
}
