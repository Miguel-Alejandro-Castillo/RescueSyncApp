import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styles from './DetalleLotes.module.css';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch, getSession } from '../../services/authService';
import CuentaRegresiva from '../../components/CuentaRegresiva';

export default function DetalleLotes() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [lotes, setLotes] = useState([]);
  const [loading, setLoading] = useState(true);


  const [loteSeleccionadoId, setLoteSeleccionadoId] = useState(null);

  const [idOng, setIdOng] = useState('');
  const [cantRecurso, setCantRecurso] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [convocatoriaCerrada, setConvocatoriaCerrada] = useState(false);

  const fechaLimite = lotes[0]?.fechaLimiteConvocatoria;

  useEffect(() => {
    authenticatedFetch(`${API_RESCUE}/emergencias/${id}/lotes`)
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
    const session = getSession();
    console.log('📌 [DEBUG] Sesión recuperada:', session);
    if (!session) {
      alert('Tu sesión ha expirado. Por favor, volvé a iniciar sesión.');
      return;
    }

    // 2. Extraer el ID de la ONG desde el JWT
    let currentOngId = null;
    try {
      const payloadBase64 = session.access_token.split('.')[1];
      const bytes = Uint8Array.from(
        atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')),
        (character) => character.charCodeAt(0)
      );
      const claims = JSON.parse(new TextDecoder().decode(bytes));
    
      currentOngId = claims.user_id || claims.id_ong || claims.ong_id || claims.sub;
    
    } catch (err) {
     console.log('Error al decodificar el token de usuario:', err);
      
    }

    if (!currentOngId) {
      alert('No se pudo determinar la ONG asociada a tu usuario. Verificá tu inicio de sesión.');
      return;
    }
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
        id_ong: Number(currentOngId),
        cant_recurso: Number(cantRecurso)
      };

      const response = await authenticatedFetch(`${API_RESCUE}/ofertas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al procesar la oferta');
      }

      navigate('/ofertas', { 
      state: { mensajeExito: '¡Oferta registrada con éxito!' } 
    });
      setLoteSeleccionadoId(null);
      setCantRecurso('');


      const updated = await authenticatedFetch(`${API_RESCUE}/emergencias/${id}/lotes`);
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
      <button 
    onClick={() => navigate('/ofertas')} 
    className={styles.secondaryBtn || styles.button} 
    style={{
      marginBottom: '1.5rem',
      cursor: 'pointer',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.5rem 1rem',
      borderRadius: '0.5rem',
      border: '1px solid var(--border, #ccc)',
      backgroundColor: 'transparent',
      color: 'var(--text-color, #6cb984)',
      fontWeight: '500',
      fontSize: '0.9rem',
      transition: 'all 0.2s ease'
    }}
  >
    ← Volver al portal
  </button>

      <h1>Lotes Disponibles para Emergencia #{id}</h1>

      {fechaLimite && (
        <CuentaRegresiva
          fechaLimite={fechaLimite}
          onFinalizar={() => {
            setConvocatoriaCerrada(true);
            setLoteSeleccionadoId(null);
          }}
        />
      )}

      {loading ? (
        <p>Cargando lotes...</p>
      ) : (lotes || []).length === 0 ? (
        <p>No se encontraron lotes activos para esta emergencia.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {(lotes || []).map((lote) => {
            const estaDesplegado = loteSeleccionadoId === lote.id;
            const cantCubierta = lote.cantidadCubierta || 0;
            const faltante = lote.cantidad - cantCubierta;

            return (
              <div
                key={lote.id}
                style={{
                  border: '1px solid var(--border)',
                  padding: '1.2rem',
                  borderRadius: '8px',
                  backgroundColor: 'var(--surface)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>{lote.tipo_recurso}</h3>
                    <p style={{ margin: 0, color: 'var(--muted)' }}>
                      Cubierto: <strong>{cantCubierta}</strong> de {lote.cantidad} (Faltan: <strong style={{ color: 'var(--danger)' }}>{faltante}</strong>)
                    </p>
                  </div>

                  {lote.estado !== 'cubierto' && !convocatoriaCerrada && (
                    <button
                      onClick={() => toggleFormulario(lote.id)}
                      style={{
                        padding: '0.5rem 1rem',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: estaDesplegado ? 'var(--surface-raised)' : 'var(--primary)',
                        color: estaDesplegado ? 'var(--ink)' : 'var(--on-primary)',
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
                      borderTop: '1px solid var(--border)',
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
                        <input className="form-control"
                          type="number"
                          min="1"
                          max={faltante}
                          placeholder={`Máximo ${faltante}`}
                          value={cantRecurso}
                          onChange={(e) => setCantRecurso(e.target.value)}
                          style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
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
                        backgroundColor: 'var(--primary)',
                        color: 'var(--on-primary)',
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
