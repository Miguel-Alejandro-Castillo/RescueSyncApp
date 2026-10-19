export const LOTE_ESTADOS = {
  CREADO: 'creado',
  ACTIVO: 'activo',
  ABIERTO: 'abierto',
  CUBIERTO: 'cubierto',
  REFORMULADO: 'reformulado',
  EN_ADJUDICACION: 'en_adjudicacion',
  ADJUDICADO: 'adjudicado'
};

export function isEstadoLote(value, estado) {
  return typeof value === 'string' && value.toLowerCase() === estado;
}

// capitaliza la primera letra de cada palabra y reemplaza guiones bajos por espacios
export function normalizeEstadoLote(value) {
  return typeof value === 'string' ? value.toLowerCase().replace(/_/g, ' ').replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); }) : value;
}