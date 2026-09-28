import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { obtenerEmergenciasPendientes } from '../../services/lotesService';
import styles from './AltaLotes.module.css';

export default function SeleccionarEmergencia() {
  const [emergencias, setEmergencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    obtenerEmergenciasPendientes()
      .then(data => { if (active) setEmergencias(data); })
      .catch(error => { if (active) setError(error.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  return <div className={styles.page}>
    <div className="page-heading">
      <h1>Lotes y convocatorias</h1>
      <p>Seleccioná una emergencia pendiente para definir sus recursos y publicar la convocatoria.</p>
    </div>
    {loading ? <p role="status">Cargando emergencias pendientes…</p> : error ?
      <div className="notice notice-error" role="alert">
        <p>{error}</p>
        <button className="btn btn-outline-secondary" onClick={() => setAttempt(value => value + 1)}>Reintentar</button>
      </div> : emergencias.length === 0 ?
      <div className="panel"><h2>No hay emergencias pendientes</h2><p>Las emergencias registradas que todavía no tengan una convocatoria publicada aparecerán acá.</p></div> :
      <div className="form-stack">{emergencias.map(emergencia =>
        <article className="panel" key={emergencia.id}>
          <div className={styles.row}>
            <h2>{emergencia.zonaAfectada}</h2>
            <span className="badge bg-secondary">Gravedad: {emergencia.nivelGravedad}</span>
          </div>
          <p>{emergencia.descripcionInicial}</p>
          <Link className="btn btn-primary" to={`/lotes/nuevo?emergenciaId=${encodeURIComponent(emergencia.id)}`}>Organizar lotes · Emergencia #{emergencia.id}</Link>
        </article>
      )}</div>}
  </div>;
}
