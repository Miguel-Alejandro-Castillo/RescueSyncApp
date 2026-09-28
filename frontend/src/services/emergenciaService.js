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
