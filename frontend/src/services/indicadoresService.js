import { API_RESCUE } from '../config/api';
import { authenticatedFetch } from './authService';

async function leerError(res, mensaje) {
  const data = await res.json().catch(() => null);
  return typeof data?.detail === 'string' ? data.detail : mensaje;
}

function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor) search.set(clave, valor);
  });
  const texto = search.toString();
  return texto ? `?${texto}` : '';
}

export async function obtenerIndicadores(mes) {
  const res = await authenticatedFetch(`${API_RESCUE}/dashboard/indicadores${query({ mes })}`);
  if (!res.ok) throw new Error(await leerError(res, 'No se pudieron cargar los indicadores.'));
  return res.json();
}

// Descarga el archivo generado por el backend (JSON completo o CSV de un dataset).
export async function exportarIndicadores({ formato, dataset, mes }) {
  const res = await authenticatedFetch(`${API_RESCUE}/dashboard/exportar${query({ formato, dataset, mes })}`);
  if (!res.ok) throw new Error(await leerError(res, 'No se pudo exportar el reporte.'));

  const disposicion = res.headers.get('Content-Disposition') || '';
  const nombre = /filename="([^"]+)"/.exec(disposicion)?.[1] || `rescuesync_${dataset}.${formato}`;
  const url = URL.createObjectURL(await res.blob());
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}
