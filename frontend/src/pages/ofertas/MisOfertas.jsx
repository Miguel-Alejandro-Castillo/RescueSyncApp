import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import ValidatedForm, { FieldError } from '../../components/ValidatedForm';

export default function MisOfertas() {
  const navigate = useNavigate();
  const location = useLocation();

  const [ofertas, setOfertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensajeExito, setMensajeExito] = useState(location.state?.mensajeExito || '');

  // Estado para controlar la edición
  const [editingOferta, setEditingOferta] = useState(null);
  const [nuevaCantidad, setNuevaCantidad] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const cargarMisOfertas = async () => {
    try {
      setLoading(true);
      setError('');
      // Pide directamente las ofertas del usuario autenticado por Token
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/misofertas/`);
      if (!res.ok) throw new Error('Error al cargar las ofertas');
      const data = await res.json();
      setOfertas(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError(err.message);
      setOfertas([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarMisOfertas();
  }, []);

  const handleAbrirEditar = (oferta) => {
    setError('');
    setMensajeExito('');
    setEditingOferta(oferta);
    setNuevaCantidad(oferta.cant_recurso);
  };

  const handleGuardarEdicion = async (e) => {
    e.preventDefault();
    setError('');
    if (!nuevaCantidad || Number(nuevaCantidad) <= 0) {
      setError('Ingrese una cantidad válida.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/${editingOferta.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cant_recurso: Number(nuevaCantidad),
          id_ong: Number(editingOferta.id_ong)
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al actualizar la oferta');

      setMensajeExito('Oferta actualizada correctamente.');
      setEditingOferta(null);
      cargarMisOfertas(); // Recargar datos
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Mis ofertas</h1>
      {error && <div className="notice notice-error" role="alert"><strong>No se pudo completar la acción</strong><p>{error}</p></div>}

      {mensajeExito && (
        <div className="notice notice-success" role="status">
          {mensajeExito}
        </div>
      )}

      {loading ? (
        <p>Cargando ofertas...</p>
      ) : error && ofertas.length === 0 ? null : ofertas.length === 0 ? (
        <p>No se encontraron ofertas registradas para esta ONG.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {ofertas.map((item) => (
            <div
              key={item.id}
              style={{
                border: '1px solid var(--border, #ccc)',
                padding: '1.2rem',
                borderRadius: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
                backgroundColor: 'var(--surface, #fff)'
              }}
            >
              <div>
                <h3 style={{ margin: '0 0 0.3rem 0' }}>{item.emergencia_titulo}</h3>
                <p style={{ margin: '0 0 0.5rem 0', color: '#555' }}>
                  Recurso: <strong>{item.lote_tipo}</strong> | Cantidad ofertada: <strong>{item.cant_recurso}</strong>
                </p>
                <small style={{ color: item.es_editable ? '#1e8e3e' : '#d93025', fontWeight: '500' }}>
                  {item.es_editable ? '● Convocatoria abierta' : '● Convocatoria cerrada / Finalizada'}
                </small>
              </div>

              <div>
                {item.es_editable ? (
                  <button
                    onClick={() => handleAbrirEditar(item)}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: '#1a73e8',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 'bold'
                    }}
                  >
                    Editar
                  </button>
                ) : (
                  <span style={{ fontSize: '0.85rem', color: '#888' }}>No editable</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal / Formulario Flotante para Edición */}
      {editingOferta && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="panel" role="dialog" aria-modal="true" aria-labelledby="editar-oferta-titulo" style={{ color: 'var(--ink)', padding: '2rem', width: 'min(480px, calc(100vw - 2rem))', maxHeight: '90vh', overflowY: 'auto' }}>
            <h3 id="editar-oferta-titulo">Editar oferta ({editingOferta.lote_tipo})</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>
              Emergencia: {editingOferta.emergencia_titulo}
            </p>

            <ValidatedForm onSubmit={handleGuardarEdicion} aria-busy={submitting}>
              {error && <p className="notice notice-error" role="alert">{error}</p>}
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="editar-cantidad" className="form-label">
                  Nueva cantidad a ofertar:
                </label>
                <input
                  id="editar-cantidad"
                  name="cantidadOferta"
                  data-required-message="Ingrese la nueva cantidad de la oferta."
                  step="1"
                  max={editingOferta.lote_cantidad_total - editingOferta.lote_cantidad_cubierta + editingOferta.cant_recurso}
                  type="number"
                  min="1"
                  value={nuevaCantidad}
                  onChange={(e) => setNuevaCantidad(e.target.value)}
                  className="form-control"
                  required
                />
                <FieldError name="cantidadOferta" />
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  onClick={() => setEditingOferta(null)}
                  className="btn btn-outline-secondary"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn btn-primary"
                >
                  {submitting ? 'Guardando…' : 'Guardar cambios'}
                </button>
              </div>
            </ValidatedForm>
          </div>
        </div>
      )}
    </div>
  );
}
