import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styles from './DetalleLotes.module.css';

export default function DetalleLotes() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [lotes, setLotes] = useState([]);
  const [loading, setLoading] = useState(true);
  

  const [loteSeleccionadoId, setLoteSeleccionadoId] = useState(null);

  const [idOng, setIdOng] = useState('');
  const [cantRecurso, setCantRecurso] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch(`http://127.0.0.1:3000/api/rescue/emergencias/${id}/lotes`)
      .then((res) => {
        if (!res.ok) throw new Error('Error al obtener los lotes');
        return res.json();
      })
      .then((data) => {
        setLotes(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLotes([]);
        setLoading(false);
      });
  }, [id]);

  const toggleFormulario = (loteId) => {
    if (loteSeleccionadoId === loteId) {
      setLoteSeleccionadoId(null);
    } else {
      setLoteSeleccionadoId(loteId);
      setCantRecurso('');
    }
  };

  const handleSubmitOferta = async (e, lote) => {
    e.preventDefault();

    const faltante = lote.cantidad - (lote.cant_cubierta || 0);
    

    if (!cantRecurso || Number(cantRecurso) <= 0) {
      alert('Ingresa una cantidad válida a ofertar.');
      return;
    }

    if (Number(cantRecurso) > faltante) {
      alert(`La cantidad ofertada no puede ser mayor a la requerida (${faltante}).`);
      return;
    }

    try {
      setSubmitting(true);

    
      const payload = {
        id_lote: Number(lote.id),
        id_ong: 1,
        cant_recurso: Number(cantRecurso)
      };

      const response = await fetch('http://127.0.0.1:3000/api/rescue/ofertas/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al procesar la oferta');
      }

      alert('¡Oferta registrada con éxito!');
      setLoteSeleccionadoId(null);
      setCantRecurso('');

      
      const updated = await fetch(`http://127.0.0.1:3000/api/rescue/emergencias/${id}/lotes`);
      const updatedData = await updated.json();
      setLotes(Array.isArray(updatedData) ? updatedData : []);

    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page} style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer' }}>
        ← Volver al portal
      </button>

      <h1>Lotes Disponibles para Emergencia #{id}</h1>

      {loading ? (
        <p>Cargando lotes...</p>
      ) : (lotes || []).length === 0 ? (
        <p>No se encontraron lotes activos para esta emergencia.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {(lotes || []).map((lote) => {
            const estaDesplegado = loteSeleccionadoId === lote.id;
            const cantCubierta = lote.cant_cubierta || 0;
            const faltante = lote.cantidad - cantCubierta;

            return (
              <div 
                key={lote.id} 
                style={{ 
                  border: '1px solid #ccc', 
                  padding: '1.2rem', 
                  borderRadius: '8px',
                  backgroundColor: '#fff'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>{lote.tipo_recurso}</h3>
                    <p style={{ margin: 0, color: '#555' }}>
                      Cubierto: <strong>{cantCubierta}</strong> de {lote.cantidad} (Faltan: <strong style={{ color: '#e53e3e' }}>{faltante}</strong>)
                    </p>
                  </div>

                  {lote.estado !== 'cubierto' && (
                    <button 
                      onClick={() => toggleFormulario(lote.id)}
                      style={{
                        padding: '0.5rem 1rem',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: estaDesplegado ? '#e2e8f0' : '#2b6cb0',
                        color: estaDesplegado ? '#2d3748' : '#fff',
                        fontWeight: 'bold'
                      }}
                    >
                      {estaDesplegado ? 'Cancelar' : 'Cargar Oferta'}
                    </button>
                  )}
                </div>

                {}
                {estaDesplegado && (
                  <form 
                    onSubmit={(e) => handleSubmitOferta(e, lote)}
                    style={{ 
                      marginTop: '1rem', 
                      paddingTop: '1rem', 
                      borderTop: '1px dashed #cbd5e0',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.8rem'
                    }}
                  >
                    <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
                      
                        

                      <div style={{ flex: '1 1 200px' }}>
                        <label style={{ display: 'block', fontWeight: '600', fontSize: '0.85rem', marginBottom: '0.2rem' }}>
                          Cantidad a ofertar (Máx: {faltante}):
                        </label>
                        <input 
                          type="number" 
                          min="1"
                          max={faltante}
                          placeholder={`Máximo ${faltante}`}
                          value={cantRecurso}
                          onChange={(e) => setCantRecurso(e.target.value)}
                          style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                          required
                        />
                      </div>
                    </div>

                    <button 
                      type="submit" 
                      disabled={submitting}
                      style={{
                        alignSelf: 'flex-start',
                        padding: '0.6rem 1.2rem',
                        backgroundColor: '#38a169',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        fontWeight: 'bold',
                        cursor: submitting ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {submitting ? 'Guardando...' : 'Confirmar Oferta'}
                    </button>
                  </form>
                )}

              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}