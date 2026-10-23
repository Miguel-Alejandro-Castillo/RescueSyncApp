export const EMERGENCIA_ESTADOS = {
  CREADA: 'creada',
  PUBLICADA: 'publicada',
  CONVOCATORIA_CERRADA: 'convocatoria_cerrada',
};

// Decisión del Centro Coordinador cuando la convocatoria cierra sin cobertura suficiente
export const ACCIONES_COORDINADOR = [
  { value: 'reabrir', label: 'Reabrir la convocatoria', descripcion: 'Los lotes elegidos vuelven a recibir ofertas durante una nueva ventana de tiempo.' },
  { value: 'reformular', label: 'Reformular lotes', descripcion: 'Los lotes elegidos se reemplazan por lotes nuevos y se abre una nueva convocatoria.' },
  { value: 'parcial', label: 'Continuar con cobertura parcial', descripcion: 'Se sigue a la adjudicación sólo con los recursos que tienen respaldo, aunque no alcancen lo pedido.' },
];

export function isEstadoEmergencia(value, estado) {
  return typeof value === 'string' && value.toLowerCase() === estado;
}