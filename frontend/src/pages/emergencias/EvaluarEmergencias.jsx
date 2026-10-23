import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { obtenerEmergenciasPendientesDecision, decidirEmergencia } from '../../services/lotesService';
import { getNivelGravedadLabel } from '../../constants/gravedad';
import { ACCIONES_COORDINADOR } from '../../constants/emergencia';
import ResultadoValidacion from '../../components/ResultadoValidacion';
import styles from './EvaluarEmergencias.module.css';

export default function EvaluarEmergencias() {
  const [emergencias, setEmergencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  useEffect(() => {
    obtenerEmergenciasPendientesDecision()
      .then(data => setEmergencias(Array.isArray(data) ? data : []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleResuelta = (id, texto) => {
    setEmergencias(lista => lista.filter(e => e.id !== id));
    setMensaje(texto);
  };

  return (
    <div className="panel">
      <h1>Evaluar emergencias</h1>
      <p className={styles.intro}>
        Emergencias cuya convocatoria terminó sin cubrir todo lo pedido. Revisá todas sus ofertas y decidí cómo seguir con la emergencia.
      </p>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice notice-success" role="status"><p>{mensaje}</p></div>}

      {loading ? (
        <p>Cargando emergencias…</p>
      ) : emergencias.length === 0 ? (
        <p>No hay emergencias esperando una decisión.</p>
      ) : (
        <div className={styles.list}>
          {emergencias.map(emergencia => (
            <EvaluacionEmergencia key={emergencia.id} emergencia={emergencia} onResuelta={handleResuelta} />
          ))}
        </div>
      )}
    </div>
  );
}

function EvaluacionEmergencia({ emergencia, onResuelta }) {
  const navigate = useNavigate();
  const noCubiertos = emergencia.lotes.filter(lote => !lote.cubierto);
  const [accion, setAccion] = useState('');
  const [elegidos, setElegidos] = useState(noCubiertos.map(lote => lote.id));
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  const eligeLotes = accion === 'reabrir' || accion === 'reformular';
  const puedeConfirmar = accion && (!eligeLotes || elegidos.length > 0) && !enviando;

  const toggleLote = (id) => {
    setElegidos(actual => actual.includes(id) ? actual.filter(x => x !== id) : [...actual, id]);
  };

  const handleConfirmar = async () => {
    setError('');
    if (accion === 'reformular') {
      // Los lotes nuevos se definen en el formulario de lotes, que envía la decisión completa.
      navigate(`/lotes/nuevo?emergenciaId=${emergencia.id}&reformular=${elegidos.join(',')}`);
      return;
    }
    try {
      setEnviando(true);
      const respuesta = await decidirEmergencia(emergencia.id, { accion, lotes: accion === 'reabrir' ? elegidos : [] });
      onResuelta(emergencia.id, `${emergencia.zonaAfectada}: ${respuesta.mensaje}`);
    } catch (err) {
      setError(err.message);
      setEnviando(false);
    }
  };

  return (
    <section className={styles.emergency} aria-labelledby={`emergencia-${emergencia.id}`}>
      <header className={styles.heading}>
        <h2 id={`emergencia-${emergencia.id}`}>{emergencia.zonaAfectada}</h2>
        <span className={styles.context}>
          Urgencia: {getNivelGravedadLabel(emergencia.nivelGravedad)} · {emergencia.lotes.length - noCubiertos.length} de {emergencia.lotes.length} lotes cubiertos
        </span>
        <p className={styles.context}>{emergencia.descripcionInicial}</p>
      </header>

      {emergencia.lotes.map(lote => (
        <details key={lote.id} className={styles.lote}>
          <summary className={styles.loteHeading}>
            <div className={styles.loteTitle}>
              <h3>{lote.tipoRecurso} · {lote.descripcion}</h3>
              <div className={styles.quantities}>
                <span>Se necesitan <strong>{lote.cantidad}</strong></span>
                <span>Con respaldo: <strong>{lote.ofertado_valido}</strong></span>
                {!lote.cubierto && <span>Faltan <strong>{lote.faltante}</strong></span>}
                <span>{lote.ofertas.length} {lote.ofertas.length === 1 ? 'oferta' : 'ofertas'}</span>
              </div>
            </div>
            <span className={styles.badge} data-state={lote.cubierto ? 'cubierto' : 'faltante'}>
              {lote.cubierto ? 'Cubierto' : 'No cubierto'}
            </span>
          </summary>
          <div className={styles.loteBody}>
            {lote.ofertas.length === 0 ? (
              <p className={styles.context}>Ninguna ONG ofertó para este lote.</p>
            ) : lote.ofertas.map(oferta => (
              <div key={oferta.id} className={styles.oferta}>
                <p>
                  <strong>Oferta #{oferta.id}</strong> · ofrece {oferta.cantidad_ofertada} ·{' '}
                  <span className={oferta.valida ? styles.valida : styles.invalida}>{oferta.valida ? 'Válida' : 'Inválida'}</span>
                </p>
                <ResultadoValidacion resultado={oferta.resultado_validacion} fecha={oferta.validada_en} />
              </div>
            ))}
          </div>
        </details>
      ))}

      <fieldset className={styles.decision} disabled={enviando}>
        <legend>¿Cómo sigue esta emergencia?</legend>
        {ACCIONES_COORDINADOR.map(opcion => (
          <label key={opcion.value} className={styles.opcion}>
            <input type="radio" name={`accion-${emergencia.id}`} value={opcion.value}
              checked={accion === opcion.value} onChange={() => setAccion(opcion.value)} />
            <span>
              <strong>{opcion.label}</strong>
              <small>{opcion.descripcion}</small>
            </span>
          </label>
        ))}

        {eligeLotes && (
          <div className={styles.lotesElegidos}>
            <p>{accion === 'reabrir' ? 'Lotes a reabrir:' : 'Lotes a reformular:'}</p>
            {noCubiertos.map(lote => (
              <label key={lote.id} className={styles.opcion}>
                <input type="checkbox" checked={elegidos.includes(lote.id)} onChange={() => toggleLote(lote.id)} />
                <span>{lote.tipoRecurso} · {lote.descripcion} (faltan {lote.faltante})</span>
              </label>
            ))}
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="btn btn-primary" onClick={handleConfirmar} disabled={!puedeConfirmar}>
            {enviando ? 'Confirmando…' : accion === 'reformular' ? 'Definir los lotes nuevos' : 'Confirmar decisión'}
          </button>
        </div>
        {error && <p className="notice notice-error" role="alert">{error}</p>}
      </fieldset>
    </section>
  );
}
