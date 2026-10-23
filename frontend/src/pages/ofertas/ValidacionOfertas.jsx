import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { authenticatedFetch, getSessionMemberships } from '../../services/authService';
import { API_RESCUE } from '../../config/api';
import ResultadoValidacion from '../../components/ResultadoValidacion';
import { useSession } from '../../auth/AuthContext';
import { canAccess } from '../../auth/permissions';
import { ejemplosValidacion } from './ejemplosValidacion';
import { ACCIONES_COORDINADOR } from '../../constants/emergencia';
import styles from './ValidacionOfertas.module.css';

function DecisionCoordinador({ decisiones }) {
  const ultima = decisiones?.at(-1);
  if (!ultima) return null;
  const label = ACCIONES_COORDINADOR.find(a => a.value === ultima.accion)?.label || ultima.accion;
  return <p className={styles.decision}>
    Decisión del coordinador: {label}{ultima.fecha && ` · ${new Date(ultima.fecha).toLocaleString('es-AR')}`}
  </p>;
}

function CoberturaRecurso({ lote }) {
  if (lote.cantidad == null) return null;
  const cobertura = lote.ofertas[0]?.resultado_validacion?.cobertura_lote;
  const pendientes = !cobertura?.completa;
  const cubierta = cobertura?.ofertado_valido;
  const completa = cobertura?.cubierto === true;
  return <div className={styles.coverage} data-state={completa ? 'completa' : pendientes ? 'pendiente' : 'insuficiente'}>
    <strong>{completa ? 'Cantidad necesaria alcanzada' : pendientes ? 'Cobertura por confirmar' : 'Cantidad necesaria no alcanzada'}</strong>
    {cubierta != null && <span>{cubierta} de {lote.cantidad} unidades cubiertas{!completa && !pendientes ? ` · Faltan ${cobertura.faltante}` : ''}</span>}
    {pendientes && <span>La cobertura debe confirmarse con el Sistema Nacional.</span>}
  </div>;
}

export default function ValidacionOfertas({ demo = false }) {
  const [ofertas, setOfertas] = useState(demo ? ejemplosValidacion : []);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!demo);
  const session = useSession();
  const coordinador = canAccess(getSessionMemberships(session), 'emergencias.evaluar');
  const emergencias = Object.values(ofertas.reduce((grupos, oferta) => {
    const emergencia = grupos[oferta.emergencia_id] ||= { id: oferta.emergencia_id, zona: oferta.emergencia_zona, gravedad: oferta.emergencia_gravedad, decisiones: oferta.decisiones_coordinador, lotes: {} };
    const lote = emergencia.lotes[oferta.lote_id] ||= { id: oferta.lote_id, descripcion: oferta.lote_descripcion, cantidad: oferta.lote_cantidad, ofertas: [] };
    lote.ofertas.push(oferta);
    return grupos;
  }, {}));
  useEffect(() => {
    if (demo) return;
    let active = true;
    async function cargar() {
      try {
        const response = await authenticatedFetch(`${API_RESCUE}/ofertas-validacion`);
        if (!response.ok) throw new Error('No se pudieron cargar los resultados de validación.');
        const data = await response.json();
        if (active) { setOfertas(data); setError(''); }
      } catch (e) { if (active) setError(e.message); }
      finally { if (active) setLoading(false); }
    }
    cargar();
    const timer = setInterval(cargar, 10000);
    return () => { active = false; clearInterval(timer); };
  }, [demo]);
  return <div className="panel">
    <h1>Validación de ofertas</h1>
    {demo && <p className={styles.demo} role="status">Datos de ejemplo para explorar la pantalla. No se ejecutan consultas ni se modifican ofertas reales.</p>}
    {!demo && coordinador && <Link to="/emergencias/evaluar">Evaluar emergencias sin cobertura suficiente</Link>}
    {error && <p className="notice notice-error" role="alert">{error}</p>}
    <div className={styles.list}>
    {loading ? <p>Cargando ofertas…</p> : ofertas.length === 0 ? <p>No hay ofertas registradas.</p> : emergencias.map(emergencia =>
      <section key={emergencia.id} className={styles.emergency}>
        <header className={styles.emergencyHeading}>
          <h2>{emergencia.zona || 'Emergencia sin ubicación registrada'}</h2>
          {emergencia.gravedad && <span className={styles.context}>Urgencia: {emergencia.gravedad}</span>}
          <DecisionCoordinador decisiones={emergencia.decisiones} />
        </header>
        {Object.values(emergencia.lotes).map(lote => {
          const cobertura = lote.ofertas[0]?.resultado_validacion?.cobertura_lote;
          const ofrecida = cobertura?.cantidad_ofertada;
          const estado = !cobertura?.completa ? 'pendiente' : cobertura.cubierto ? 'valida' : 'invalida';
          return <details key={lote.id} className={styles.resource} open={demo || undefined}>
          <summary className={styles.resourceHeading}>
            <div className={styles.heading}>
              <h3>{lote.descripcion}</h3>
              <div className={styles.resourceQuantities}>
                {lote.cantidad != null && <span>Se necesitan <strong>{lote.cantidad} unidades</strong></span>}
                <span>Cantidad ofrecida: <strong>{ofrecida != null ? `${ofrecida} unidades` : 'Sin consultar'}</strong></span>
              </div>
            </div>
            <span className={styles.badge} data-state={estado}>{({ valida: 'Cumple', invalida: 'No cumple', pendiente: 'Pendiente' })[estado]}</span>
          </summary>
          <div className={styles.resourceBody}>
          <CoberturaRecurso lote={lote} />
          <ResultadoValidacion resultado={{ participantes: lote.ofertas.flatMap(o =>
            !o.resultado_validacion?.error && o.estado_validacion !== 'pendiente'
              ? (o.resultado_validacion?.participantes || []).map((p, i) => ({ ...p, participante_id: `${o.id}-${p.participante_id ?? i}` }))
              : []
          ) }} />
          {lote.ofertas.filter(o => !o.resultado_validacion || o.resultado_validacion.error || o.estado_validacion === 'pendiente').map(o =>
            <ResultadoValidacion key={o.id} resultado={o.resultado_validacion?.error ? o.resultado_validacion : null} />
          )}
          {lote.ofertas.filter(o => o.resultado_validacion?.cantidad_aceptada != null).map(o => <p key={o.id} className={styles.decision}>
            {(o.resultado_validacion.participantes || []).map(p => p.ong_nombre).filter(Boolean).join(' + ') || `Oferta #${o.id}`}: {o.resultado_validacion.cantidad_aceptada} unidades aceptadas con cobertura parcial
          </p>)}
          </div>
        </details>;
        })}
      </section>)}
    </div>
  </div>;
}
