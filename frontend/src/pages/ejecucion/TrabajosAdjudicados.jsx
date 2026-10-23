import { useState, useEffect } from 'react';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import styles from './TrabajosAdjudicados.module.css';

async function leerError(res, mensaje) {
  const data = await res.json().catch(() => null);
  return typeof data?.detail === 'string' ? data.detail : mensaje;
}

export default function TrabajosAdjudicados() {
  const [emergencias, setEmergencias] = useState([]);
  const [confirmando, setConfirmando] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const cargar = async () => {
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/ejecucion/mis-emergencias`);
      if (!res.ok) throw new Error(await leerError(res, 'Error al cargar los trabajos adjudicados'));
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
    setEnviando(true);
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/ejecucion/emergencias/${emergenciaId}/trabajo-finalizado`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await leerError(res, 'Error al informar el trabajo finalizado'));
      setMensaje('Informaste al Centro Coordinador que tu ONG terminó su trabajo.');
      setConfirmando(null);
      await cargar();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Trabajos adjudicados</h1>
      <p className={styles.intro}>
        Emergencias en las que el municipio aceptó recursos de tu ONG. Cuando terminen el trabajo, informalo al Centro Coordinador.
      </p>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice notice-success" role="status"><p>{mensaje}</p></div>}

      {loading ? (
        <p>Cargando trabajos...</p>
      ) : emergencias.length === 0 ? (
        <p>Tu ONG todavía no tiene recursos adjudicados.</p>
      ) : (
        <div className={styles.lista}>
          {emergencias.map(emergencia => (
            <section key={emergencia.id} className={styles.item}>
              <h2>Emergencia #{emergencia.id} - {emergencia.zona}</h2>
              <p>Recursos adjudicados a tu ONG:</p>
              <ul>
                {emergencia.lotes.map(lote => (
                  <li key={lote.lote_id}>{lote.tipo} - {lote.descripcion}: {lote.cantidad_adjudicada}</li>
                ))}
              </ul>

              {emergencia.finalizado_en ? (
                <p className={styles.finalizado}>
                  Trabajo finalizado el {new Date(emergencia.finalizado_en).toLocaleString()}.
                </p>
              ) : !emergencia.en_ejecucion ? (
                <p className={styles.aviso}>La emergencia todavía no está en ejecución o ya se cerró.</p>
              ) : confirmando === emergencia.id ? (
                <div className={styles.confirmacion}>
                  <p>¿Confirmás que tu ONG terminó su trabajo en esta emergencia? No se puede deshacer.</p>
                  <button type="button" className="btn btn-primary" disabled={enviando} onClick={() => handleFinalizar(emergencia.id)}>
                    {enviando ? 'Informando…' : 'Sí, terminamos'}
                  </button>
                  <button type="button" className="btn btn-outline-secondary" disabled={enviando} onClick={() => setConfirmando(null)}>
                    Cancelar
                  </button>
                </div>
              ) : (
                <button type="button" className="btn btn-primary" onClick={() => setConfirmando(emergencia.id)}>
                  Trabajo finalizado
                </button>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
