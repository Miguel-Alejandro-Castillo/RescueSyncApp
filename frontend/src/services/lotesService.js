import { API_RESCUE } from '../config/api';
import { authenticatedFetch } from './authService';
import { EMERGENCIA_ESTADOS } from '../constants/emergencia';

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
  const data = await request(`/emergencias?estado=${EMERGENCIA_ESTADOS.CREADA}`);
  if (!Array.isArray(data)) throw new Error('No se pudo interpretar el listado de emergencias.');
  return data.filter(emergencia => emergencia.estado === EMERGENCIA_ESTADOS.CREADA);
}

export const obtenerEmergenciaPorId = id => request(`/emergencias/${encodeURIComponent(id)}`);

export const crearLotes = payload => request('/lotes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const reformularLotes = payload => request('/lotes/reformular', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const reabrirConvocatoria = ofertaId => request('/lotes/reabrir', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ ofertaId }),
});

export const obtenerLote = loteId => request(`/lotes/${encodeURIComponent(loteId)}`);

export const obtenerOfertasLote = loteId => request(`/lotes/${encodeURIComponent(loteId)}/ofertas`);