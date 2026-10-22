/** Validación sin reservas: cada oferta se verifica independientemente. */
export function comprobarSolicitud(data) {
  const fail = () => { throw Object.assign(new Error('Lotes, ofertas o participantes inválidos'), { status: 400, code: 'INVALID_VALIDATION_REQUEST' }); };
  const id = value => Number.isSafeInteger(value) && value > 0;
  const cantidad = value => Number.isSafeInteger(value) && value >= 0;
  if (!data || !id(data.emergencia_id) || !Array.isArray(data.lotes) || !data.lotes.length) fail();
  const lotes = new Set(), ofertas = new Set(), participantes = new Set();
  for (const lote of data.lotes) {
    if (!id(lote.lote_id) || lotes.has(lote.lote_id) || !cantidad(lote.cantidad_requerida) || lote.cantidad_requerida === 0 || !Array.isArray(lote.ofertas)) fail();
    if (lote.recurso_codigo != null && (typeof lote.recurso_codigo !== 'string' || !lote.recurso_codigo.trim())) fail();
    lotes.add(lote.lote_id);
    for (const oferta of lote.ofertas) {
      if (!id(oferta.oferta_id) || ofertas.has(oferta.oferta_id) || !Array.isArray(oferta.participantes)) fail();
      if (oferta.cantidad_aceptada != null && !cantidad(oferta.cantidad_aceptada)) fail();
      ofertas.add(oferta.oferta_id);
      for (const p of oferta.participantes) {
        if (!id(p.participante_id) || !id(p.ong_id) || participantes.has(p.participante_id) || !cantidad(p.cantidad_ofertada)) fail();
        if (p.cuit != null && (typeof p.cuit !== 'string' || p.cuit.length > 32)) fail();
        participantes.add(p.participante_id);
      }
    }
  }
}

function evaluarOferta(oferta, lote, inventarios) {
  if (!lote.recurso_codigo) return { error: 'El lote no tiene vinculado un código de recurso nacional' };
  if (oferta.participantes.some(p => !p.cuit?.trim())) {
    return { error: 'El aporte no tiene registrada su ONG de origen. Hay que revisar su vinculación histórica.' };
  }
  const aportes = new Map();
  const participantes = oferta.participantes.map(p => {
    const cuit = p.cuit.trim();
    const ong = inventarios.get(cuit);
    const recurso = ong?.recursos.find(r => r.recurso.codigo === lote.recurso_codigo);
    let disponible = 0, motivo = null;
    if (!ong) motivo = 'ONG no registrada en el Sistema Nacional';
    else if (ong.estado !== 'HABILITADA') motivo = 'ONG no habilitada en el Sistema Nacional';
    else if (!recurso) motivo = 'La ONG no tiene registrado el recurso solicitado';
    else disponible = Math.max(0, recurso.cantidadTotal - recurso.cantidadReservada);
    const previo = aportes.get(cuit) || 0;
    const verificada = Math.min(p.cantidad_ofertada, Math.max(0, disponible - previo));
    aportes.set(cuit, previo + p.cantidad_ofertada);
    if (verificada < p.cantidad_ofertada && !motivo) motivo = 'Disponibilidad insuficiente para el aporte comprometido';
    return { participante_id: p.participante_id, ong_id: p.ong_id, cuit,
      ong_nacional_id: ong?.id ?? null, ong_nombre: ong?.razonSocial ?? null,
      recurso_codigo: lote.recurso_codigo, cantidad_ofertada: p.cantidad_ofertada,
      cantidad_disponible: disponible, cantidad_verificada: verificada,
      faltante: p.cantidad_ofertada - verificada, valida: motivo === null, motivo };
  });
  const valida = participantes.length > 0 && participantes.every(p => p.valida);
  const resultado = { valida, inventario_valido: valida, participantes,
    motivo: participantes.length ? null : 'La oferta no tiene aportes confirmados',
    cantidad_ofertada: participantes.reduce((n, p) => n + p.cantidad_ofertada, 0),
    cantidad_verificada: participantes.reduce((n, p) => n + p.cantidad_verificada, 0) };
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

export async function validarEmergencia(data, consultarInventarios) {
  comprobarSolicitud(data);
  const cuits = [...new Set(data.lotes.flatMap(l => l.ofertas.flatMap(o => o.participantes.map(p => p.cuit?.trim()).filter(Boolean))))];
  const inventarios = new Map((cuits.length ? await consultarInventarios(cuits) : []).map(o => [o.cuit, o]));
  const resultados = [], cobertura_por_lote = [];
  for (const lote of data.lotes) {
    const ofertas = lote.ofertas.map(o => {
      const resultado = evaluarOferta(o, lote, inventarios);
      return { oferta_id: o.oferta_id, lote_id: lote.lote_id,
        estado_validacion: resultado.error ? 'pendiente' : resultado.valida ? 'valida' : 'invalida',
        resultado_validacion: resultado };
    });
    const completa = ofertas.every(o => o.estado_validacion !== 'pendiente');
    const ofertado_valido = ofertas.reduce((n, o) => {
      const r = o.resultado_validacion;
      return n + (r.error ? 0 : r.cantidad_aceptada ?? (r.inventario_valido ? r.cantidad_verificada : 0));
    }, 0);
    const cobertura = { lote_id: lote.lote_id, requerido: lote.cantidad_requerida,
      cantidad_ofertada: lote.ofertas.reduce((n, o) => n + o.participantes.reduce((m, p) => m + p.cantidad_ofertada, 0), 0),
      ofertado_valido, faltante: Math.max(0, lote.cantidad_requerida - ofertado_valido), completa,
      cubierto: completa && ofertado_valido >= lote.cantidad_requerida };
    if (completa && !cobertura.cubierto) {
      for (const o of ofertas) {
        const r = o.resultado_validacion;
        if (!r.inventario_valido) continue;
        r.valida = false;
        r.motivo = `Las ofertas con recursos suficientes cubren ${ofertado_valido} de ${lote.cantidad_requerida} unidades del lote.`;
        r.faltante_cobertura_lote = cobertura.faltante;
        o.estado_validacion = 'invalida';
      }
    }
    for (const o of ofertas) o.resultado_validacion.cobertura_lote = cobertura;
    resultados.push(...ofertas);
    cobertura_por_lote.push(cobertura);
  }
  const pendientes = resultados.filter(o => o.estado_validacion === 'pendiente').length;
  return { emergencia_id: data.emergencia_id, completa: pendientes === 0,
    cobertura_suficiente: pendientes === 0 && cobertura_por_lote.every(l => l.cubierto),
    cobertura_por_lote, ofertas_validas: resultados.filter(o => o.estado_validacion === 'valida').length,
    ofertas_invalidas: resultados.filter(o => o.estado_validacion === 'invalida').length,
    ofertas_pendientes: pendientes, resultados };
}
