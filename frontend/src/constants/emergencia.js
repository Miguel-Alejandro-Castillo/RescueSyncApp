export const EMERGENCIA_ESTADOS = {
  CREADA: 'creada',
  PUBLICADA: 'publicada',
  CONVOCATORIA_CERRADA: 'convocatoria_cerrada',
};

export function isEstadoEmergencia(value, estado) {
  return typeof value === 'string' && value.toLowerCase() === estado;
}