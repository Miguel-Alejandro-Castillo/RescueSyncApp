import { API_RESCUE, ENDPOINTS } from '../config/api';
import { authenticatedFetch } from './authService';

export const adjudicarOfertas = async (loteId, data) => {

    // Si sale bien no retorna contenido, solo un status 204
    const response = await authenticatedFetch(`${ENDPOINTS.OFERTAS}/${loteId}/adjudicaciones`, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        let message = 'No se pudo confirmar la adjudicación.';

        try {
            const payload = await response.json();
            message = payload?.detail || payload?.message || message;
        } catch {
            try {
                const text = await response.text();
                if (text) {
                    message = text;
                }
            } catch {
                // Se conserva el mensaje por defecto.
            }
        }

        throw new Error(message);
    }

    return true;
};
