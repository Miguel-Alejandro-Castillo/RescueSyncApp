export function parsearFechaUTC(valor) {
  if (!valor) return null;
  const tieneZona = /(Z|[+-]\d{2}:?\d{2})$/.test(valor);
  const fecha = new Date(tieneZona ? valor : `${valor}Z`);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

export function calcularRestanteMs(fechaLimite, ahora = Date.now()) {
  return Math.max(0, fechaLimite.getTime() - ahora);
}

export function formatearRestante(ms) {
  const totalSegundos = Math.floor(Math.max(0, ms) / 1000);
  const horas = Math.floor(totalSegundos / 3600);
  const minutos = Math.floor((totalSegundos % 3600) / 60);
  const segundos = totalSegundos % 60;
  return [horas, minutos, segundos].map(n => String(n).padStart(2, '0')).join(':');
}
