import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { authenticatedFetch, getSessionMemberships } from '../../services/authService';
import { API_RESCUE } from '../../config/api';
import ResultadoValidacion from '../../components/ResultadoValidacion';
import { useSession } from '../../auth/AuthContext';
import { canAccess } from '../../auth/permissions';
import { ejemplosValidacion } from './ejemplosValidacion';
import styles from './ValidacionOfertas.module.css';

function CoberturaRecurso({ lote }) {
  if (lote.cantidad == null) return null;
  const pendientes = lote.ofertas.some(o => !o.resultado_validacion || o.resultado_validacion.error || o.estado_validacion === 'pendiente');
  const cubierta = lote.ofertas.reduce((total, o) => {
    const resultado = o.resultado_validacion;
    if (!resultado || resultado.error || o.estado_validacion === 'pendiente') return total;
    if (resultado.cantidad_aceptada != null) return total + resultado.cantidad_aceptada;
    const suficiente = resultado.inventario_valido ?? (resultado.participantes?.length > 0 && resultado.participantes.every(p => p.valida));
    return total + (suficiente ? (resultado.cantidad_verificada ?? 0) : 0);
  }, 0);
  const completa = cubierta >= lote.cantidad;
  return <div className={styles.coverage} data-state={completa ? 'completa' : pendientes ? 'pendiente' : 'insuficiente'}>
    <strong>{completa ? 'Cantidad necesaria alcanzada' : pendientes ? 'Cobertura por confirmar' : 'Cantidad necesaria no alcanzada'}</strong>
    <span>{cubierta} de {lote.cantidad} unidades cubiertas{!completa && !pendientes ? ` · Faltan ${lote.cantidad - cubierta}` : ''}</span>
    {pendientes && <span>Hay ofertas sin verificar.</span>}
  </div>;
}

export default function ValidacionOfertas({ demo = false }) {
  const [ofertas, setOfertas] = useState(demo ? ejemplosValidacion : []);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!demo);
  const [catalogo, setCatalogo] = useState([]);
  const [selecciones, setSelecciones] = useState({});
  const [guardando, setGuardando] = useState(null);
  const session = useSession();
  const coordinador = canAccess(getSessionMemberships(session), 'ofertas.ver_invalidas');
  const emergencias = Object.values(ofertas.reduce((grupos, oferta) => {
    const emergencia = grupos[oferta.emergencia_id] ||= { id: oferta.emergencia_id, zona: oferta.emergencia_zona, gravedad: oferta.emergencia_gravedad, lotes: {} };
    const lote = emergencia.lotes[oferta.lote_id] ||= { id: oferta.lote_id, descripcion: oferta.lote_descripcion, cantidad: oferta.lote_cantidad, ofertas: [] };
    lote.ofertas.push(oferta);
    return grupos;
  }, {}));
  useEffect(() => {
    if (demo || !coordinador) return;
    let active = true;
    authenticatedFetch(`${API_RESCUE}/recursos-nacionales`).then(async r => {
      if (!r.ok) throw new Error('No se pudo cargar el catálogo nacional.');
      const data = await r.json();
      if (active) setCatalogo(data);
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [coordinador, demo]);
  async function vincular(loteId) {
    setGuardando(loteId);
    try {
      const r = await authenticatedFetch(`${API_RESCUE}/lotes/${loteId}/recurso-nacional`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codigo: selecciones[loteId] }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'No se pudo vincular el recurso.');
      setOfertas(lista => lista.map(o => o.lote_id === loteId ? { ...o, recurso_codigo: data.recurso_codigo } : o));
      setError('');
    } catch (e) { setError(e.message); }
    finally { setGuardando(null); }
  }
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
    {!demo && coordinador && <Link to="/ofertas-invalidas">Resolver ofertas inválidas</Link>}
    {error && <p className="notice notice-error" role="alert">{error}</p>}
    <div className={styles.list}>
    {loading ? <p>Cargando ofertas…</p> : ofertas.length === 0 ? <p>No hay ofertas registradas.</p> : emergencias.map(emergencia =>
      <section key={emergencia.id} className={styles.emergency}>
        <header className={styles.emergencyHeading}>
          <h2>{emergencia.zona || 'Emergencia sin ubicación registrada'}</h2>
          {emergencia.gravedad && <span className={styles.context}>Urgencia: {emergencia.gravedad}</span>}
        </header>
        {Object.values(emergencia.lotes).map(lote => {
          const ofrecida = lote.ofertas.reduce((total, o) => total + (o.resultado_validacion?.cantidad_ofertada ?? 0), 0);
          const pendiente = lote.ofertas.some(o => !o.resultado_validacion || o.resultado_validacion.error || o.estado_validacion === 'pendiente');
          const cubierta = lote.ofertas.reduce((total, o) => {
            const r = o.resultado_validacion;
            if (!r || r.error || o.estado_validacion === 'pendiente') return total;
            const suficiente = r.inventario_valido ?? (r.participantes?.length > 0 && r.participantes.every(p => p.valida));
            return total + (r.cantidad_aceptada ?? (suficiente ? (r.cantidad_verificada ?? 0) : 0));
          }, 0);
          const estado = lote.cantidad == null || pendiente ? 'pendiente' : cubierta >= lote.cantidad ? 'valida' : 'invalida';
          return <details key={lote.id} className={styles.resource} open={demo || undefined}>
          <summary className={styles.resourceHeading}>
            <div className={styles.heading}>
              <h3>{lote.descripcion}</h3>
              <div className={styles.resourceQuantities}>
                {lote.cantidad != null && <span>Se necesitan <strong>{lote.cantidad} unidades</strong></span>}
                <span>Cantidad ofrecida: <strong>{ofrecida} unidades</strong>{pendiente ? ' (registradas hasta ahora)' : ''}</span>
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
          {lote.ofertas.slice(0, 1).map(o => <div key={o.id}>
        {!demo && coordinador && !o.recurso_codigo && <div>
          <label htmlFor={`recurso-oferta-${o.id}`}>Vincular este lote al recurso nacional</label>
          <select id={`recurso-oferta-${o.id}`} className="form-select" value={selecciones[o.lote_id] || ''}
            onChange={e => setSelecciones({ ...selecciones, [o.lote_id]: e.target.value })}>
            <option value="">Seleccionar recurso</option>
            {catalogo.map(r => <option key={r.codigo} value={r.codigo}>{r.nombre} ({r.codigo})</option>)}
          </select>
          <button className="btn btn-primary" disabled={!selecciones[o.lote_id] || guardando !== null}
            onClick={() => vincular(o.lote_id)}>{guardando === o.lote_id ? 'Guardando…' : 'Vincular recurso'}</button>
        </div>}
          </div>)}
          {lote.ofertas.filter(o => o.accion_tomada).map(o => <p key={o.id} className={styles.decision}>
            {(o.resultado_validacion?.participantes || []).map(p => p.ong_nombre).filter(Boolean).join(' + ') || 'Decisión del coordinador'}: {({ reabrir: 'Reabrir convocatoria', reformular: 'Reformular lotes', parcial: 'Continuar con cobertura parcial' })[o.accion_tomada]}
            {o.resultado_validacion?.cantidad_aceptada != null && ` · ${o.resultado_validacion.cantidad_aceptada} unidades aceptadas`}
          </p>)}
          </div>
        </details>;
        })}
      </section>)}
    </div>
  </div>;
}
