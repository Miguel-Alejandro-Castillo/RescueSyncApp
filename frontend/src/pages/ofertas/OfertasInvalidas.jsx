import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { decidirOfertasInvalidasEmergencia, obtenerDecisionesPendientes } from '../../services/lotesService';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import { LOTE_ESTADOS } from '../../constants/lote';
import styles from './OfertasInvalidas.module.css';
import ResultadoValidacion from '../../components/ResultadoValidacion';
import ConfirmModal from '../../components/ConfirmModal';

const ACCIONES = [
  { value: 'reabrir', label: 'Reabrir convocatoria' },
  { value: 'reformular', label: 'Reformular cantidades' },
  { value: 'parcial', label: 'Continuar con cobertura parcial' },
];

async function cargarOfertas() {
  const res = await authenticatedFetch(`${API_RESCUE}/ofertas/invalidas`);
  if (!res.ok) throw new Error('Error al cargar las ofertas inválidas');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

function agruparPorEmergencia(ofertas, pendientes) {
  const porEmergencia = Object.fromEntries(pendientes.map(pendiente => [
    pendiente.id, { id: pendiente.id, zona: pendiente.zona, ofertas: [], pendiente },
  ]));
  return Object.entries(ofertas.reduce((grupos, oferta) => {
    const key = oferta.emergencia_id ?? `sin-emergencia-${oferta.id}`;
    if (!grupos[key]) {
      grupos[key] = {
        id: oferta.emergencia_id,
        zona: oferta.emergencia_zona || 'Emergencia sin identificar',
        ofertas: [],
      };
    }
    grupos[key].ofertas.push(oferta);
    return grupos;
  }, porEmergencia));
}

function LotesDeEmergencia({ ofertas, lotesSinOfertas }) {
  const porLote = new Map();
  for (const oferta of ofertas) {
    if (!porLote.has(oferta.id_lote)) porLote.set(oferta.id_lote, []);
    porLote.get(oferta.id_lote).push(oferta);
  }

  return (
    <div className={styles.lotes}>
      {[...porLote].map(([id, ofertasLote]) => {
        const lote = ofertasLote[0];
        return (
          <details key={id} className={styles.lote}>
            <summary>
              <span className={styles.filaLote}>
                <span><strong>{lote.lote_descripcion || 'Recurso sin identificar'}</strong><span className={styles.secundario}> · Lote #{id}</span></span>
                <span className={styles.secundario}>Requeridas: {lote.lote_cantidad}</span>
                <span>{lotesSinOfertas.includes(id) ? 'Sin ofertas nuevas' : `${ofertasLote.length} ${ofertasLote.length === 1 ? 'oferta' : 'ofertas'}`}</span>
              </span>
            </summary>
            <div className={styles.ofertas}>
              {ofertasLote.map(oferta => <DetalleOferta key={oferta.id} oferta={oferta} />)}
            </div>
          </details>
        );
      })}
      {lotesSinOfertas.filter(id => !porLote.has(id)).map(id => (
        <div key={id} className={styles.loteVacio}>
          <strong>Lote #{id}</strong>
          <span className={styles.secundario}>Sin ofertas</span>
        </div>
      ))}
    </div>
  );
}

function DetalleOferta({ oferta }) {
  return (
    <section className={styles.oferta}>
      <h3>Oferta #{oferta.id}</h3>
      <p>Cantidad ofertada: <strong>{oferta.cantidad_ofertada}</strong> · ONG líder: {oferta.ong_lider_nombre || 'Sin identificar'}</p>
      <ResultadoValidacion resultado={oferta.resultado_validacion} fecha={oferta.validada_en} />
      {oferta.lotes_nuevos?.length > 0 && (
        <div>
          <p>Lotes derivados:</p>
          <ul>{oferta.lotes_nuevos.map(lote => (
            <li key={lote.id}>{lote.tipo} — {lote.descripcion} (pedido: {lote.cantidad}, cubierto: {lote.cantidad_cubierta})</li>
          ))}</ul>
        </div>
      )}
      {oferta.descartada_en ? (
        <p>Oferta descartada por {oferta.motivo_descarte === 'reapertura' ? 'reapertura' : 'reformulación'} el {new Date(oferta.descartada_en).toLocaleString('es-AR', { hour12: false })}.</p>
      ) : oferta.lote_estado === LOTE_ESTADOS.REFORMULADO ? (
        <p>El lote fue reformulado.</p>
      ) : null}
    </section>
  );
}

export default function OfertasInvalidas() {
  const navigate = useNavigate();
  const [ofertas, setOfertas] = useState([]);
  const [pendientes, setPendientes] = useState([]);
  const [acciones, setAcciones] = useState({});
  const [loading, setLoading] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [modalConfig, setModalConfig] = useState({ isOpen: false, emergenciaId: null, accion: null, title: '', message: '' });
  const grupos = useMemo(() => agruparPorEmergencia(ofertas, pendientes), [ofertas, pendientes]);

  const actualizarGrupos = async () => {
    const [ofertasActuales, decisiones] = await Promise.all([cargarOfertas(), obtenerDecisionesPendientes()]);
    setOfertas(ofertasActuales);
    setPendientes(decisiones);
  };

  useEffect(() => {
    actualizarGrupos()
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleConfirmar = (grupo) => {
    setError('');
    setMensaje('');
    const accion = acciones[grupo.id];
    if (!accion || !grupo.pendiente) return;
    const loteIds = accion === 'parcial' ? grupo.pendiente.lotes_invalidos : grupo.pendiente.lotes_reabribles;
    const messages = {
      reabrir: {
        title: 'Reabrir convocatoria',
        message: 'Se reabrirá la convocatoria de los lotes con ofertas inválidas y sin ninguna oferta válida.',
      },
      reformular: {
        title: 'Reformular cantidades',
        message: 'Podrás modificar las cantidades de los lotes con ofertas inválidas y sin ninguna oferta válida.',
      },
      parcial: {
        title: 'Continuar con cobertura parcial',
        message: 'Se aceptarán las cantidades verificadas de las ofertas inválidas. Todos los lotes activos pasarán a adjudicación.',
      },
    };
    setModalConfig({ isOpen: true, emergenciaId: grupo.id, loteIds, accion, ...messages[accion] });
  };

  const ejecutarAccion = async () => {
    const { emergenciaId, accion, loteIds = [] } = modalConfig;
    setModalConfig(current => ({ ...current, isOpen: false }));
    if (!emergenciaId || !accion || guardando) return;
    if (accion === 'reformular') {
      navigate(`/lotes/nuevo?emergenciaId=${emergenciaId}&reformularEmergencia=true&loteIds=${loteIds.join(',')}`);
      return;
    }
    setGuardando(true);
    try {
      await decidirOfertasInvalidasEmergencia(emergenciaId, { accion, lote_ids: loteIds });
      await actualizarGrupos();
      setMensaje(accion === 'reabrir'
        ? 'La convocatoria se reabrió para los lotes inválidos de la emergencia.'
        : 'Se aceptaron las cantidades verificadas de las ofertas inválidas y todos los lotes activos pasaron a adjudicación.');
      setAcciones(current => ({ ...current, [emergenciaId]: '' }));
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Decisiones por emergencia</h1>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice" role="status"><p>{mensaje}</p></div>}

      {loading ? (
        <p>Cargando emergencias...</p>
      ) : grupos.length === 0 ? (
        <p>No hay emergencias con decisiones pendientes.</p>
      ) : (
        <div className={styles.lista}>
          {grupos.map(([clave, grupo]) => {
            const pendiente = grupo.pendiente;
            const decision = grupo.ofertas.find(oferta => !oferta.descartada_en && oferta.accion_tomada)?.accion_tomada;
            const accionesDisponibles = ACCIONES.filter(accion => accion.value === 'parcial' || pendiente?.lotes_reabribles.length);
            return (
              <section key={clave} className={styles.item}>
                <header className={styles.encabezado}>
                  <div>
                    {grupo.id && <span className={styles.secundario}>Emergencia #{grupo.id}</span>}
                    <h2>{grupo.zona}</h2>
                  </div>
                  {pendiente ? (
                    <div>
                      <label htmlFor={`accion-${grupo.id}`} className="form-label">Acción para toda la emergencia</label>
                      <div className={styles.accion}>
                        <select
                          id={`accion-${grupo.id}`}
                          className="form-select"
                          value={acciones[grupo.id] || ''}
                          disabled={guardando}
                          onChange={event => setAcciones(current => ({ ...current, [grupo.id]: event.target.value }))}
                        >
                          <option value="">Seleccionar acción</option>
                          {accionesDisponibles.map(accion => <option key={accion.value} value={accion.value}>{accion.label}</option>)}
                        </select>
                        <button type="button" className="btn btn-primary" onClick={() => handleConfirmar(grupo)} disabled={guardando || !accionesDisponibles.some(accion => accion.value === acciones[grupo.id])}>
                          Confirmar decisión
                        </button>
                      </div>
                    </div>
                  ) : decision ? (
                    <p>Decisión registrada: <strong>{ACCIONES.find(item => item.value === decision)?.label || decision}</strong>.</p>
                  ) : <p>Esta emergencia no tiene decisiones pendientes.</p>}
                </header>
                <LotesDeEmergencia ofertas={grupo.ofertas} lotesSinOfertas={pendiente?.lotes_sin_ofertas ?? []} />
              </section>
            );
          })}
        </div>
      )}

      <ConfirmModal
        isOpen={modalConfig.isOpen}
        title={modalConfig.title}
        message={modalConfig.message}
        confirmVariant="primary"
        onConfirm={ejecutarAccion}
        onCancel={() => setModalConfig(current => ({ ...current, isOpen: false }))}
      />
    </div>
  );
}
