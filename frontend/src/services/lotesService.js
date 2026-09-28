// Configuración de la URL del Backend a través de variables de entorno de Vite
const API_BASE_URL = import.meta.env.VITE_API_RESCUE_URL || 'http://localhost:3000';
const API_PREFIX = import.meta.env.VITE_API_RESCUE || '/api/rescue';
// Servicio temporal: reemplazar por la llamada HTTP cuando esté disponible.
export const crearLotes = async () =>
  new Promise((resolve) => {
    setTimeout(() => resolve({ success: true }), 500);
  });
export const obtenerEmergenciaPorId = async (id) => {
    try {
        const response = await fetch(`${API_BASE_URL}${API_PREFIX}/emergencias/${id}`);
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error(`No se encontró ninguna emergencia con el ID ${id}.`);
            }
            throw new Error(`Error del servidor al buscar la emergencia (${response.status})`);
        }

        return await response.json();
    } catch (error) {
        console.error("Error en obtenerEmergenciaPorId:", error);
        throw error;
    }
};