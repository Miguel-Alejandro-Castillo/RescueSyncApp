import { useState, useEffect } from 'react';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import styles from './Monitoreo.module.css';

async function leerError(res, mensaje) {
  const data = await res.json().catch(() => null);
  return typeof data?.detail === 'string' ? data.detail : mensaje;
}

export default function Monitoreo() {
  const [emergencias, setEmergencias] = useState([]);
  const [textos, setTextos] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  const cargar = async () => {
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/monitoreo`);
      if (!res.ok) throw new Error(await leerError(res, 'Error al cargar el monitoreo'));
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

  const handleRegistrar = async (loteId) => {
    setError('');
    setMensaje('');
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/monitoreo/lotes/${loteId}/eventos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ descripcion: textos[loteId] || '' })
      });
      if (!res.ok) throw new Error(await leerError(res, 'Error al registrar el evento'));
      setTextos({ ...textos, [loteId]: '' });
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleFinalizar = async (emergenciaId) => {
    setError('');
    setMensaje('');
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/monitoreo/emergencias/${emergenciaId}/finalizar`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await leerError(res, 'Error al finalizar el monitoreo'));
      setMensaje('Monitoreo finalizado correctamente.');
      await cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Monitoreo de la ejecución</h1>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice notice-success" role="status">{mensaje}</div>}

      {loading ? (
        <p>Cargando monitoreo...</p>
      ) : emergencias.length === 0 ? (
        <p>No hay emergencias con lotes adjudicados para monitorear.</p>
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
                  disabled={!emergencia.todas_finalizaron}
                  title={emergencia.todas_finalizaron ? undefined : 'Todas las ONGs tienen que informar que terminaron su trabajo'}
                >
                  Finalizar monitoreo
                </button>
              </div>

              <div className={styles.ongs}>
                <h3>ONGs adjudicadas</h3>
                {emergencia.ongs.length === 0 ? (
                  <p>Todavía no hay ONGs adjudicadas.</p>
                ) : (
                  <ul>
                    {emergencia.ongs.map(ong => (
                      <li key={ong.cuit}>
                        {ong.nombre}:{' '}
                        {ong.finalizado_en
                          ? <span className={styles.finalizado}>terminó su trabajo el {new Date(ong.finalizado_en).toLocaleString()}</span>
                          : <span className={styles.pendiente}>trabajando</span>}
                      </li>
                    ))}
                  </ul>
                )}
                {!emergencia.todas_finalizaron && (
                  <p className={styles.aviso}>
                    El monitoreo se puede finalizar cuando todas las ONGs informen que terminaron
                    ({emergencia.ongs.filter(o => o.finalizado_en).length} de {emergencia.ongs.length}).
                  </p>
                )}
              </div>

              {emergencia.lotes.map(lote => (
                <div key={lote.id} className={styles.lote}>
                  <h3>{lote.tipo} - {lote.descripcion} (cantidad: {lote.cantidad})</h3>

                  <label htmlFor={`evento-${lote.id}`} className="form-label">Nuevo evento:</label>
                  <div className={styles.formulario}>
                    <input
                      id={`evento-${lote.id}`}
                      type="text"
                      className="form-control"
                      maxLength={500}
                      value={textos[lote.id] || ''}
                      onChange={e => setTextos({ ...textos, [lote.id]: e.target.value })}
                    />
                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={() => handleRegistrar(lote.id)}
                    >
                      Registrar evento
                    </button>
                  </div>

                  {lote.eventos.length === 0 ? (
                    <p>Todavía no hay eventos registrados.</p>
                  ) : (
                    <ul>
                      {lote.eventos.map(evento => (
                        <li key={evento.id}>
                          {new Date(evento.fecha).toLocaleString()} - {evento.descripcion}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
