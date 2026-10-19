export const NIVELES_GRAVEDAD = {
  BAJO: 'bajo',
  MEDIO: 'medio',
  ALTO: 'alto',
  CRITICO: 'critico',
};

export const GRAVEDAD_OPTIONS = [
  { value: NIVELES_GRAVEDAD.BAJO, label: 'Bajo' },
  { value: NIVELES_GRAVEDAD.MEDIO, label: 'Medio' },
  { value: NIVELES_GRAVEDAD.ALTO, label: 'Alto' },
  { value: NIVELES_GRAVEDAD.CRITICO, label: 'Crítico' },
];

export function normalizeNivelGravedad(value) {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

export function isNivelGravedad(value, nivel) {
  return normalizeNivelGravedad(value) === nivel;
}

export function getNivelGravedadLabel(value) {
  switch (normalizeNivelGravedad(value)) {
    case NIVELES_GRAVEDAD.CRITICO:
      return 'Crítica';
    case NIVELES_GRAVEDAD.ALTO:
      return 'Alta';
    case NIVELES_GRAVEDAD.MEDIO:
      return 'Media';
    case NIVELES_GRAVEDAD.BAJO:
      return 'Baja';
    default:
      return value || 'Sin definir';
  }
}