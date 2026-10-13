import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { reabrirConvocatoria } from '../../services/lotesService';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import styles from './OfertasInvalidas.module.css';

const ACCIONES = [
  { value: 'reabrir', label: 'Reabrir la convocatoria' },
  { value: 'reformular', label: 'Reformular lotes' },
  { value: 'parcial', label: 'Continuar con cobertura parcial' },
];

export default function OfertasInvalidas() {
  const navigate = useNavigate();
  const [ofertas, setOfertas] = useState([]);
  const [acciones, setAcciones] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const cargar = async () => {
      try {
        const res = await authenticatedFetch(`${API_RESCUE}/ofertas/invalidas`);
        if (!res.ok) throw new Error('Error al cargar las ofertas inválidas');
        const data = await res.json();
        setOfertas(Array.isArray(data) ? data : []);
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

  const handleConfirmar = async (id) => {
    setError('');
    try {
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/${id}/accion`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accion: acciones[id] })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al confirmar la acción');
      const oferta = ofertas.find(o => o.id === id);
      if (acciones[id] === 'reformular') {
        navigate(`/lotes/nuevo?emergenciaId=${oferta.emergencia_id}&ofertaId=${id}`);
        return;
      }
      setOfertas(ofertas.map(o => o.id === id ? { ...o, accion_tomada: acciones[id] } : o));
      if (acciones[id] === 'reabrir') {
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
      setOfertas(lista => lista.map(o => o.id === id ? { ...o, convocatoria_abierta: true } : o));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.page}>
      <h1>Ofertas inválidas</h1>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}

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
              <p>ONG líder: {oferta.ong_lider_id}</p>
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
              {oferta.accion_tomada === 'reformular' && oferta.lote_estado !== 'reformulado' && (
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
              {oferta.lote_estado === 'reformulado' && <p>Los lotes ya fueron reformulados.</p>}
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
