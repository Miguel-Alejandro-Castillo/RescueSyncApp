import { ENDPOINTS } from "../config/api";
import { authenticatedFetch } from "./authService";

export async function crearEmergencia(emergencia) {
  const response = await authenticatedFetch(ENDPOINTS.EMERGENCIAS, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(emergencia),
  });

  if (!response.ok) throw new Error("No se pudo registrar la emergencia");
  return response.status === 204 ? null : response.json();
}

export async function obtenerEmergencias(userId) {
  const response = await authenticatedFetch(`${ENDPOINTS.EMERGENCIAS}?usuarioCreador=${userId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new Error("No se pudieron obtener las emergencias");
  return response.status === 204 ? null : response.json();
}

export async function obtenerLotes(emergenciaId) {
  const response = await authenticatedFetch(`${ENDPOINTS.EMERGENCIAS}/${emergenciaId}/lotes`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) throw new Error("No se pudieron obtener los lotes");
  return response.status === 204 ? null : response.json();
}
  