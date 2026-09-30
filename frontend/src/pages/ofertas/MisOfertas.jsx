import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';

export default function MisOfertas() {
  const navigate = useNavigate();
  const location = useLocation();

  const [ofertas, setOfertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mensajeExito, setMensajeExito] = useState(location.state?.mensajeExito || '');

  // Estado para controlar la edición
  const [editingOferta, setEditingOferta] = useState(null);
  const [nuevaCantidad, setNuevaCantidad] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const cargarMisOfertas = async () => {
    try {
      setLoading(true);
      // Pide directamente las ofertas del usuario autenticado por Token
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/misofertas`);
      if (!res.ok) throw new Error('Error al cargar las ofertas');
      const data = await res.json();
      setOfertas(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setOfertas([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarMisOfertas();
  }, []);

  const handleAbrirEditar = (oferta) => {
    setEditingOferta(oferta);
    setNuevaCantidad(oferta.cant_recurso);
  };

  const handleGuardarEdicion = async (e) => {
    e.preventDefault();
    if (!nuevaCantidad || Number(nuevaCantidad) <= 0) {
      alert('Ingresá una cantidad válida.');
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
      alert(`Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Mis Ofertas Registradas</h1>

      {mensajeExito && (
        <div style={{ padding: '1rem', backgroundColor: '#e6f4ea', color: '#137333', borderRadius: '6px', marginBottom: '1rem' }}>
          {mensajeExito}
        </div>
      )}

      {loading ? (
        <p>Cargando ofertas...</p>
      ) : ofertas.length === 0 ? (
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
          <div style={{ backgroundColor: '#fff', padding: '2rem', borderRadius: '8px', minWidth: '320px' }}>
            <h3>Editar Oferta ({editingOferta.lote_tipo})</h3>
            <p style={{ fontSize: '0.9rem', color: '#666' }}>
              Emergencia: {editingOferta.emergencia_titulo}
            </p>

            <form onSubmit={handleGuardarEdicion}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.3rem', fontWeight: 'bold' }}>
                  Nueva cantidad a ofertar:
                </label>
                <input
                  type="number"
                  min="1"
                  value={nuevaCantidad}
                  onChange={(e) => setNuevaCantidad(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setEditingOferta(null)}
                  style={{ padding: '0.5rem 1rem', background: '#ccc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  style={{ padding: '0.5rem 1rem', background: '#1a73e8', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  {submitting ? 'Guardando...' : 'Guardar Cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}