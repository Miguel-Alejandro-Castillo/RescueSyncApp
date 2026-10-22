import { useState, useEffect } from 'react';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import styles from './Monitoreo.module.css';

async function leerError(res, mensaje) {
  const data = await res.json().catch(() => null);
  return typeof data?.detail === 'string' ? data.detail : mensaje;
}

export default function TareasAdjudicadas() {
  const [emergencias, setEmergencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const cargar = async () => {
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/monitoreo/mis-tareas`);
      if (!res.ok) throw new Error(await leerError(res, 'Error al cargar las tareas'));
      const data = await res.json();
      setEmergencias(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const handleFinalizar = async (emergenciaId) => {
    setError('');
    setMensaje('');
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/monitoreo/emergencias/${emergenciaId}/tareas-finalizadas`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await leerError(res, 'Error al finalizar las tareas'));
      setMensaje('Tareas finalizadas correctamente.');
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Mis tareas adjudicadas</h1>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice notice-success" role="status">{mensaje}</div>}

      {loading ? (
        <p>Cargando tareas...</p>
      ) : emergencias.length === 0 ? (
        <p>No tenés tareas adjudicadas pendientes.</p>
      ) : (
        <div className={styles.lista}>
          {emergencias.map(emergencia => (
            <section key={emergencia.id} className={styles.item}>
              <div className={styles.encabezado}>
                <h2>Emergencia #{emergencia.id} - {emergencia.zona}</h2>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleFinalizar(emergencia.id)}
                  disabled={emergencia.finalizada}
                >
                  {emergencia.finalizada ? 'Tareas finalizadas' : 'Marcar tareas finalizadas'}
                </button>
              </div>
              <ul>
                {emergencia.lotes.map(lote => (
                  <li key={lote.id}>
                    {lote.tipo} - {lote.descripcion} (adjudicado a tu ONG: {lote.cantidad_adjudicada})
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
