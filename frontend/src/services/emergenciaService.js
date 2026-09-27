import { ENDPOINTS } from "../config/api";

export async function crearEmergencia(emergencia) {
  const response = await fetch(ENDPOINTS.EMERGENCIAS, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(emergencia),
  });

  if (!response.ok) throw new Error("No se pudo registrar la emergencia");
  return response.status === 204 ? null : response.json();
}
