import { API_RESCUE } from '../config/api';
import { authenticatedFetch } from './authService';

async function request(path, options) {
  const response = await authenticatedFetch(`${API_RESCUE}${path}`, options);
  if (!response.ok) {
    if (response.status === 403) throw new Error('No tenés permiso para realizar esta acción.');
    if (response.status === 401) throw new Error('Tu sesión venció. Iniciá sesión nuevamente.');
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'No se pudo completar la solicitud. Intentá nuevamente.');
  }
  return response.json();
}
export async function obtenerEmergenciasPendientes() {
  const data = await request('/emergencias?estado=creada');
  if (!Array.isArray(data)) throw new Error('No se pudo interpretar el listado de emergencias.');
  return data.filter(emergencia => emergencia.estado === 'creada');
}
export const obtenerEmergenciaPorId = id => request(`/emergencias/${encodeURIComponent(id)}`);
export const crearLotes = payload => request('/lotes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});
