import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styles from './DetalleLotes.module.css';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch, getSession } from '../../services/authService';
import CuentaRegresiva from '../../components/CuentaRegresiva';
import ValidatedForm, { FieldError } from '../../components/ValidatedForm';

export default function DetalleLotes() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [lotes, setLotes] = useState([]);
  const [ongsDisponibles, setOngsDisponibles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [loteSeleccionadoId, setLoteSeleccionadoId] = useState(null);
  const [cantRecurso, setCantRecurso] = useState('');
  const [ongsInvitadas, setOngsInvitadas] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [convocatoriaCerrada, setConvocatoriaCerrada] = useState(false);

  const fechaLimite = lotes[0]?.fechaLimiteConvocatoria;

  // Cargar lotes de la emergencia y la lista de ONGs de Bonita
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // 1. Obtener lotes de la emergencia
        const resLotes = await authenticatedFetch(`${API_RESCUE}/emergencias/${id}/lotes`);
        if (!resLotes.ok) throw new Error('Error al obtener los lotes');
        const dataLotes = await resLotes.json();
        setLotes(Array.isArray(dataLotes) ? dataLotes : []);

        // 2. Obtener lista de ONGs disponibles desde Bonita
        const resOngs = await authenticatedFetch(`${API_RESCUE}/ofertas/ongs-bonita`);
        if (resOngs.ok) {
          const dataOngs = await resOngs.json();
          setOngsDisponibles(Array.isArray(dataOngs) ? dataOngs : []);
        }
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const toggleFormulario = (loteId) => {
    setError('');
    if (loteSeleccionadoId === loteId) {
      setLoteSeleccionadoId(null);
    } else {
      setLoteSeleccionadoId(loteId);
      setCantRecurso('');
      setOngsInvitadas({});
    }
  };

  const handleCheckboxChange = (ongId) => {
    setOngsInvitadas(prev => ({
      ...prev,
      [ongId]: !prev[ongId]
    }));
  };

  const handleSubmitOferta = async (e, lote) => {
    e.preventDefault();
    setError('');
    const session = getSession();
    if (!session) {
      setError('Su sesión venció. Inicie sesión nuevamente.');
      return;
    }

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
      setError('No se pudo identificar la ONG asociada a su cuenta.');
      return;
    }

    const faltante = lote.cantidad - (lote.cantidadCubierta || 0);

    if (!cantRecurso || Number(cantRecurso) <= 0) {
      setError('Ingrese una cantidad válida a ofertar.');
      return;
    }

    if (Number(cantRecurso) > faltante) {
      setError(`Puede ofrecer hasta ${faltante} unidades.`);
      return;
    }

    const idsInvitados = Object.keys(ongsInvitadas)
      .filter(ongId => ongsInvitadas[ongId] && Number(ongId) !== Number(currentOngId))
      .map(Number);

    try {
      setSubmitting(true);

      const payload = {
        id_lote: Number(lote.id),
        cantidad_lider: Number(cantRecurso),
        invitados: idsInvitados
      };

      const response = await authenticatedFetch(`${API_RESCUE}/ofertas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al procesar la oferta en consorcio');
      }

      navigate('/ofertas', { 
        state: { mensajeExito: '¡Oferta en consorcio creada con éxito!' } 
      });

    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page} style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      {error && <div className="notice notice-error" role="alert"><strong>No se pudo completar la acción</strong><p>{error}</p></div>}
      
      <button 
        onClick={() => navigate('/ofertas')} 
        style={{ marginBottom: '1.5rem', cursor: 'pointer', padding: '0.5rem 1rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
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
              <div key={lote.id} style={{ border: '1px solid var(--border)', padding: '1.2rem', borderRadius: '8px', backgroundColor: 'var(--surface)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>{lote.tipoRecurso}</h3>
                    <p>{lote.descripcion}</p>
                    <p style={{ margin: 0, color: 'var(--muted)' }}>
                      Cubierto: <strong>{cantCubierta}</strong> de {lote.cantidad} (Faltan: <strong style={{ color: 'var(--danger)' }}>{faltante}</strong>)
                    </p>
                  </div>

                  {lote.estado !== 'cubierto' && !convocatoriaCerrada && (
                    <button
                      onClick={() => toggleFormulario(lote.id)}
                      style={{ padding: '0.5rem 1rem', cursor: 'pointer', borderRadius: '6px', backgroundColor: estaDesplegado ? 'var(--surface-raised)' : 'var(--primary)', color: estaDesplegado ? 'var(--ink)' : 'var(--on-primary)', fontWeight: 'bold' }}
                    >
                      {estaDesplegado ? 'Cancelar' : 'Crear oferta en consorcio'}
                    </button>
                  )}
                </div>

                {estaDesplegado && (
                  <ValidatedForm
                    onSubmit={(e) => handleSubmitOferta(e, lote)}
                    style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '1rem' }}
                  >
                    <div>
                      <label htmlFor={`oferta-cantidad-${lote.id}`} style={{ display: 'block', fontWeight: '600', fontSize: '0.85rem', marginBottom: '0.2rem' }}>
                        Tu aporte inicial (Máx: {faltante}):
                      </label>
                      <input 
                        className="form-control"
                        id={`oferta-cantidad-${lote.id}`}
                        name="cantidadOferta"
                        step="1"
                        type="number"
                        min="1"
                        max={faltante}
                        placeholder={`Máximo ${faltante}`}
                        value={cantRecurso}
                        onChange={(e) => setCantRecurso(e.target.value)}
                        style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
                        required
                      />
                      <FieldError name="cantidadOferta" />
                    </div>

                    <div style={{ marginTop: '0.5rem' }}>
                      <label style={{ display: 'block', fontWeight: '600', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                        Invitar a otras ONGs a este consorcio (opcional):
                      </label>
                      <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid var(--border)', padding: '0.5rem', borderRadius: '4px', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                        {ongsDisponibles.length === 0 ? (
                          <p style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>No hay otras ONGs disponibles para invitar.</p>
                        ) : (
                          ongsDisponibles.map((ong) => (
                            <label key={ong.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', cursor: 'pointer' }}>
                              <input 
                                type="checkbox"
                                checked={!!ongsInvitadas[ong.id]}
                                onChange={() => handleCheckboxChange(ong.id)}
                              />
                              {ong.nombre || `ONG #${ong.id}`}
                            </label>
                          ))
                        )}
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={submitting}
                      style={{ alignSelf: 'flex-start', padding: '0.6rem 1.2rem', backgroundColor: 'var(--primary)', color: 'var(--on-primary)', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: submitting ? 'not-allowed' : 'pointer' }}
                    >
                      {submitting ? 'Creando consorcio…' : 'Confirmar y Enviar Invitaciones'}
                    </button>
                  </ValidatedForm>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}