import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { reabrirConvocatoria } from '../../services/lotesService';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import { LOTE_ESTADOS } from '../../constants/lote';
import styles from './OfertasInvalidas.module.css';
import ResultadoValidacion from '../../components/ResultadoValidacion';
import ConfirmModal from '../../components/ConfirmModal';

const ACCIONES = [
  { value: 'reabrir', label: 'Reabrir la convocatoria' },
  { value: 'reformular', label: 'Reformular lotes' },
  { value: 'parcial', label: 'Continuar con cobertura parcial' },
];

async function cargarOfertas() {
  const res = await authenticatedFetch(`${API_RESCUE}/ofertas/invalidas`);
  if (!res.ok) throw new Error('Error al cargar las ofertas inválidas');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export default function OfertasInvalidas() {
  const navigate = useNavigate();
  const [ofertas, setOfertas] = useState([]);
  const [acciones, setAcciones] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [modalConfig, setModalConfig] = useState({ isOpen: false, id: null, accion: null, title: '', message: '' });

  useEffect(() => {
    const cargar = async () => {
      try {
        setOfertas(await cargarOfertas());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    cargar();
  }, []);

  const handleAccion = (id, valor) => {
    setAcciones({ ...acciones, [id]: valor });
  };

  const handleConfirmar = (id) => {
    setError('');
    setMensaje('');
    const accion = acciones[id];
    if (!accion) return;

    if (accion === 'reabrir') {
      setModalConfig({
        isOpen: true,
        id,
        accion,
        title: 'Reabrir convocatoria',
        message: '¿Está seguro de que desea reabrir la convocatoria? Se liberarán las reservas actuales y se extenderá la ventana de tiempo para recibir nuevas ofertas.',
        confirmVariant: 'primary',
      });
    } else if (accion === 'parcial') {
      setModalConfig({
        isOpen: true,
        id,
        accion,
        title: 'Continuar con cobertura parcial',
        message: '¿Está seguro de que desea continuar con cobertura parcial? Se adjudicará únicamente la cantidad verificada y se cerrará la evaluación de esta oferta.',
        confirmVariant: 'primary',
      });
    } else if (accion === 'reformular') {
      setModalConfig({
        isOpen: true,
        id,
        accion,
        title: 'Reformular lotes',
        message: '¿Desea avanzar a la reformulación de lotes para esta emergencia?',
        confirmVariant: 'primary',
      });
    }
  };

  const ejecutarAccion = async () => {
    const { id, accion } = modalConfig;
    setModalConfig({ ...modalConfig, isOpen: false });
    if (!id || !accion) return;

    try {
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/${id}/accion`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accion })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al confirmar la acción');
      const oferta = ofertas.find(o => o.id === id);
      if (accion === 'reformular') {
        navigate(`/lotes/nuevo?emergenciaId=${oferta.emergencia_id}&ofertaId=${id}`);
        return;
      }
      setOfertas(ofertas.map(o => o.id === id ? { ...o, accion_tomada: accion } : o));
      if (accion === 'reabrir') {
        await handleReabrir(id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReabrir = async (id) => {
    setError('');
    try {
      await reabrirConvocatoria(id);
      setOfertas(await cargarOfertas());
      setMensaje('Convocatoria reabierta. Las ofertas anteriores quedaron descartadas.');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Ofertas inválidas</h1>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {mensaje && <div className="notice" role="status"><p>{mensaje}</p></div>}

      {loading ? (
        <p>Cargando ofertas...</p>
      ) : ofertas.length === 0 ? (
        <p>No hay ofertas inválidas.</p>
      ) : (
        <div className={styles.lista}>
          {ofertas.map(oferta => (
            <details key={oferta.id} className={styles.item}>
              <summary>
                Oferta #{oferta.id} - {oferta.lote_tipo} ({oferta.emergencia_zona})
              </summary>
              <p>
                Lote viejo: <strong>{oferta.lote_tipo}</strong> - {oferta.lote_descripcion} (pedido: {oferta.lote_cantidad})
              </p>
              <p>Cantidad ofertada: <strong>{oferta.cantidad_ofertada}</strong></p>
              <ResultadoValidacion resultado={oferta.resultado_validacion} fecha={oferta.validada_en} />
              {oferta.lotes_nuevos.length > 0 && (
                <div>
                  <p>Lotes nuevos ofertados:</p>
                  <ul>
                    {oferta.lotes_nuevos.map(nuevo => (
                      <li key={nuevo.id}>
                        {nuevo.tipo} - {nuevo.descripcion} (pedido: {nuevo.cantidad}, cubierto: {nuevo.cantidad_cubierta})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p>ONG líder: {oferta.ong_lider_nombre || 'Sin identificar'}</p>
              {oferta.descartada_en ? (
                <p>
                  Descartada por {oferta.motivo_descarte === 'reapertura' ? 'reapertura' : 'reformulación'}
                  {' el '}{new Date(oferta.descartada_en).toLocaleString('es-AR', { hour12: false })}.
                </p>
              ) : oferta.lote_estado === LOTE_ESTADOS.REFORMULADO ? (
                <p>Los lotes ya fueron reformulados.</p>
              ) : (
              <>
              <label htmlFor={`accion-${oferta.id}`} className="form-label">Acción a tomar:</label>
              <div className={styles.accion}>
                <select
                  id={`accion-${oferta.id}`}
                  className="form-control"
                  value={oferta.accion_tomada || acciones[oferta.id] || ''}
                  onChange={e => handleAccion(oferta.id, e.target.value)}
                  disabled={Boolean(oferta.accion_tomada)}
                >
                  <option value="">Seleccionar acción</option>
                  {ACCIONES.map(accion => (
                    <option key={accion.value} value={accion.value}>{accion.label}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleConfirmar(oferta.id)}
                  disabled={!acciones[oferta.id] || Boolean(oferta.accion_tomada)}
                >
                  {oferta.accion_tomada ? 'Confirmada' : 'Confirmar'}
                </button>
              </div>
              {oferta.accion_tomada === 'reformular' && oferta.lote_estado !== LOTE_ESTADOS.REFORMULADO && (
                <Link
                  className="btn btn-outline-secondary"
                  to={`/lotes/nuevo?emergenciaId=${oferta.emergencia_id}&ofertaId=${oferta.id}`}
                >
                  Reformular lotes
                </Link>
              )}
              {oferta.accion_tomada === 'reabrir' && !oferta.convocatoria_abierta && (
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => handleReabrir(oferta.id)}
                >
                  Reabrir convocatoria
                </button>
              )}
              {oferta.accion_tomada === 'reabrir' && oferta.convocatoria_abierta && <p>La convocatoria está abierta.</p>}
              </>
              )}
            </details>
          ))}
        </div>
      )}

      <ConfirmModal
        isOpen={modalConfig.isOpen}
        title={modalConfig.title}
        message={modalConfig.message}
        confirmVariant={modalConfig.confirmVariant || 'primary'}
        onConfirm={ejecutarAccion}
        onCancel={() => setModalConfig({ ...modalConfig, isOpen: false })}
      />
    </div>
  );
}
