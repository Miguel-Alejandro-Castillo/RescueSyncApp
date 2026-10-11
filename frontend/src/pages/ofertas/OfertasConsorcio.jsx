import React, { useState, useEffect } from 'react';
import styles from './OfertasConsorcio.module.css'; // o los estilos que estés usando
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';

export default function OfertasConsorcio() {
  const [ofertas, setOfertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensajeExito, setMensajeExito] = useState('');

  // Estados para el formulario de respuesta por oferta
  const [cantidadesAportadas, setCantidadesAportadas] = useState({});
  const [submittingId, setSubmittingId] = useState(null);

  const cargarOfertas = async () => {
    try {
      setLoading(true);
      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/misofertas-consorcio`);
      if (!res.ok) throw new Error('Error al cargar las ofertas en consorcio');
      const data = await res.json();
      setOfertas(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarOfertas();
  }, []);

  const handleCantidadChange = (ofertaId, valor) => {
    setCantidadesAportadas(prev => ({
      ...prev,
      [ofertaId]: valor
    }));
  };

  const handleResponderInvitacion = async (ofertaId, aceptar, faltanteOferta) => {
    setError('');
    setMensajeExito('');

    const cantidad = cantidadesAportadas[ofertaId];

    if (aceptar) {
      if (!cantidad || Number(cantidad) <= 0) {
        setError('Debes ingresar una cantidad válida mayor a 0 para aceptar.');
        return;
      }
      if (Number(cantidad) > faltanteOferta) {
        setError(`La cantidad elegida no puede superar lo que falta en esta oferta (${faltanteOferta}).`);
        return;
      }
    }

    try {
      setSubmittingId(ofertaId);

      const payload = {
        aceptar: aceptar,
        cantidad_aportada: aceptar ? Number(cantidad) : null
      };

      const res = await authenticatedFetch(`${API_RESCUE}/ofertas/${ofertaId}/responder-invitacion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Error al procesar la respuesta');
      }

      setMensajeExito(aceptar ? '¡Invitación aceptada y aporte registrado correctamente!' : 'Has rechazado la invitación.');
      // Recargar el listado para reflejar los cambios
      await cargarOfertas();

    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingId(null);
    }
  };

  if (loading) return <p>Cargando ofertas en consorcio...</p>;

  // Separar invitaciones pendientes de ofertas activas/confirmadas
  const invitacionesPendientes = ofertas.filter(o => o.estado_invitacion === 'pendiente');
  const misConsorcios = ofertas.filter(o => o.estado_invitacion !== 'pendiente');

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Ofertas en Consorcio</h1>

      {error && <div className="notice notice-error" style={{ marginBottom: '1rem' }}><p>{error}</p></div>}
      {mensajeExito && <div className="notice notice-success" style={{ marginBottom: '1rem', color: 'green' }}><p>{mensajeExito}</p></div>}

      {/* SECCIÓN 1: INVITACIONES PENDIENTES */}
      <section style={{ marginBottom: '3rem' }}>
        <h2>Invitaciones Pendientes ({invitacionesPendientes.length})</h2>
        {invitacionesPendientes.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No tienes invitaciones pendientes por responder.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {invitacionesPendientes.map((item) => {
              const lote = item.lote || {};
              const emergencia = item.emergencia || {};
              
              // Sumar los aportes reales de los participantes que ya aceptaron en ESTA oferta
              const totalAportadoOferta = (item.participantes || []).reduce(
                (acc, p) => acc + (p.cantidad_aportada || 0), 
                0
              );
              
              const faltanteOferta = Math.max(0, (lote.cantidad || 0) - totalAportadoOferta);

              return (
                <div 
                  key={item.oferta_id} 
                  style={{ border: '2px solid var(--primary)', padding: '1.2rem', borderRadius: '8px', backgroundColor: 'var(--surface-raised)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ backgroundColor: 'orange', color: '#fff', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold' }}>
                        ¡Te invitaron a colaborar!
                      </span>
                      <h3 style={{ margin: '0.5rem 0 0.2rem 0' }}>
                        {lote.tipoRecurso || 'Recurso'} - {emergencia.zonaAfectada || 'Emergencia'}
                      </h3>
                      <p style={{ margin: 0 }}>
                        Lote requerido: <strong>{lote.cantidad}</strong> | 
                        Aportado en esta oferta: <strong>{totalAportadoOferta}</strong> | 
                        Faltante en la oferta: <strong style={{ color: 'var(--danger, red)' }}>{faltanteOferta}</strong>
                      </p>
                      <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: '0.2rem' }}>Oferta en Consorcio #{item.oferta_id}</p>
                    </div>
                  </div>

                  <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '0.2rem' }}>
                        ¿Cuántas unidades puedes aportar? (Máx: {faltanteOferta})
                      </label>
                      <input 
                        type="number"
                        min="1"
                        max={faltanteOferta}
                        placeholder={`Ej: ${Math.min(10, faltanteOferta)}`}
                        value={cantidadesAportadas[item.oferta_id] || ''}
                        onChange={(e) => handleCantidadChange(item.oferta_id, e.target.value)}
                        style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', width: '180px' }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.2rem' }}>
                      <button
                        onClick={() => handleResponderInvitacion(item.oferta_id, true, faltanteOferta)}
                        disabled={submittingId === item.oferta_id}
                        style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--success, green)', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}
                      >
                        {submittingId === item.oferta_id ? 'Guardando...' : '✓ Aceptar e Invitar Stock'}
                      </button>

                      <button
                        onClick={() => handleResponderInvitacion(item.oferta_id, false, faltanteOferta)}
                        disabled={submittingId === item.oferta_id}
                        style={{ padding: '0.5rem 1rem', backgroundColor: 'transparent', border: '1px solid var(--danger, red)', color: 'var(--danger, red)', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        Rechazar
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* SECCIÓN 2: MIS CONSORCIOS ACTIVOS */}
      <section>
        <h2>Consorcios donde Participo ({misConsorcios.length})</h2>
        {misConsorcios.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No formas parte de ningún consorcio activo por el momento.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {misConsorcios.map((item) => {
              const lote = item.lote || {};
              const emergencia = item.emergencia || {};

              return (
                <div 
                  key={item.oferta_id} 
                  style={{ border: '1px solid var(--border)', padding: '1.2rem', borderRadius: '8px', backgroundColor: 'var(--surface)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3>{lote.tipoRecurso} - {emergencia.zonaAfectada}</h3>
                      <p>Rol: <strong>{item.es_lider ? 'ONG Líder 👑' : 'Colaborador 🤝'}</strong></p>
                      <p>Mi Aporte Confirmado: <strong>{item.mi_aporte || 0} unidades</strong></p>
                    </div>
                  </div>

                  {/* Lista de Participantes del Consorcio */}
                  <div style={{ marginTop: '0.8rem', padding: '0.8rem', backgroundColor: 'var(--surface-raised)', borderRadius: '6px' }}>
                    <p style={{ margin: '0 0 0.4rem 0', fontWeight: 'bold', fontSize: '0.85rem' }}>Participantes del Consorcio:</p>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.85rem' }}>
                      {(item.participantes || []).map((p, idx) => (
                        <li key={idx}>
                          ONG #{p.ong_id}: {p.cantidad_aportada !== null ? `${p.cantidad_aportada} unidades (Confirmado)` : 'Invitación pendiente'}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}