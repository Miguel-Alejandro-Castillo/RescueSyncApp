import { ENDPOINTS } from '../config/api';

export async function crearEmergencia(emergencia) {
    console.log("Creating emergencia:", emergencia);
    const response = await fetch(
        ENDPOINTS.EMERGENCIAS,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(emergencia)
        }
    );

    return await response.json();
}
