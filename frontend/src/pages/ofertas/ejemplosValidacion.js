function ejemplo(id, recurso, ofrecido, disponible, estado, contexto = {}) {
  const verificado = Math.min(ofrecido, disponible);
  return {
    id, emergencia_id: 1, lote_id: id, lote_descripcion: recurso,
    emergencia_zona: 'Inundaciones en La Plata · Tolosa', emergencia_gravedad: 'alta',
    lote_cantidad: ofrecido, recurso_codigo: `DEMO-${id}`, estado_validacion: estado,
    resultado_validacion: {
      valida: estado === 'valida', cantidad_ofertada: ofrecido, cantidad_verificada: verificado,
      participantes: [{ participante_id: id, ong_id: id, ong_nombre: `ONG Ejemplo ${id - 100}`,
        cantidad_ofertada: ofrecido, cantidad_disponible: disponible, cantidad_verificada: verificado,
        faltante: ofrecido - verificado, valida: disponible >= ofrecido,
        motivo: disponible < ofrecido ? 'Disponibilidad insuficiente para el aporte comprometido' : null }],
    }, ...contexto,
  };
}

export const ejemplosValidacion = [
  ejemplo(101, 'Agua potable', 100, 120, 'valida'),
  ejemplo(105, 'Agua potable', 40, 50, 'valida', { lote_id: 101, lote_cantidad: 100 }),
  ejemplo(102, 'Raciones de comida', 100, 60, 'invalida'),
  ejemplo(103, 'Mantas', 90, 65, 'invalida', {
    emergencia_id: 2,
    emergencia_zona: 'Evacuación en Berisso · Villa Argüello',
    resultado_validacion: {
      valida: false, cantidad_ofertada: 90, cantidad_verificada: 65,
      participantes: [
        { participante_id: 103, ong_nombre: 'ONG Ejemplo 3', cantidad_ofertada: 50, cantidad_disponible: 60, cantidad_verificada: 50, valida: true },
        { participante_id: 104, ong_nombre: 'ONG Ejemplo 4', cantidad_ofertada: 40, cantidad_disponible: 15, cantidad_verificada: 15, valida: false },
      ],
    },
  }),
  ejemplo(104, 'Botiquines', 20, 0, 'pendiente', {
    resultado_validacion: { error: 'No se pudo consultar el Sistema Nacional. La tarea de validación debe reintentarse.' },
  }),
];
