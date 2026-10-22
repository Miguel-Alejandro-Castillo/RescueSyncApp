import React, { useState, useEffect } from 'react';
import styles from './OfertasConsorcio.module.css';
import { API_RESCUE } from '../../config/api';
import { authenticatedFetch } from '../../services/authService';
import { getSession } from '../../services/authService';
export default function OfertasConsorcio() {
  const [ofertas, setOfertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mensajeExito, setMensajeExito] = useState('');

  // Estados para el formulario de respuesta por oferta
  const [cantidadesAportadas, setCantidadesAportadas] = useState({});
  const [submittingId, setSubmittingId] = useState(null);


  //obtener mi id

  let currentOngId = null;
  let currentOngName = null;
  const session = getSession();
  if (session) {
    try {
      const payloadBase64 = session.access_token.split('.')[1];
      const bytes = Uint8Array.from(
        atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')),
        (character) => character.charCodeAt(0)
      );
      const claims = JSON.parse(new TextDecoder().decode(bytes));
      currentOngId = claims.user_id || claims.id_ong || claims.ong_id || claims.sub;
      currentOngName = claims.username || claims.name || claims.nombre || session.username;
    } catch (err) {
      console.log('Error al decodificar token:', err);
    }
  }

  const [ongsDisponibles, setOngsDisponibles] = useState([]);

  // Cargar la lista de ONGs e incluir la propia ONG en el mapeo
  useEffect(() => {
    const fetchOngs = async () => {
      try {
        const res = await authenticatedFetch(`${API_RESCUE}/ofertas/ongs-bonita`);
        if (res.ok) {
          const data = await res.json();
          const listaOngs = Array.isArray(data) ? data : [];

          // Agregar la propia ONG a la lista si no está presente
          if (currentOngId && !listaOngs.some(o => Number(o.id) === Number(currentOngId))) {
            listaOngs.push({
              id: Number(currentOngId),
              nombre: currentOngName || `ONG #${currentOngId}`
            });
          }

          setOngsDisponibles(listaOngs);
        }
      } catch (err) {
        console.error('Error al cargar nombres de ONGs:', err);
      }
    };
    fetchOngs();
  }, [currentOngId, currentOngName]);

  // Helper para resolver el nombre dado el ID
  const obtenerNombreOng = (ongId) => {
    const ong = ongsDisponibles.find(o => Number(o.id) === Number(ongId));
    return ong ? ong.nombre : `ONG #${ongId}`;
  };

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
      await cargarOfertas();

    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingId(null);
    }
  };

  if (loading) {
    return (
      <div className={styles.page} style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
        <p>Cargando ofertas en consorcio...</p>
      </div>
    );
  }

  const invitacionesPendientes = ofertas.filter(o => o.estado_invitacion === 'pendiente');
  const misConsorcios = ofertas.filter(o => o.estado_invitacion !== 'pendiente');

  return (
    <div className={styles.page} style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      {error && (
        <div className="notice notice-error" role="alert" style={{ marginBottom: '1.5rem' }}>
          <strong>No se pudo completar la acción</strong>
          <p>{error}</p>
        </div>
      )}

      {mensajeExito && (
        <div className="notice notice-success" role="alert" style={{ marginBottom: '1.5rem', color: 'var(--success, green)' }}>
          <p>{mensajeExito}</p>
        </div>
      )}

      <h1>Ofertas en Consorcio</h1>

      {/* SECCIÓN 1: INVITACIONES PENDIENTES */}
      <section style={{ marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>Invitaciones Pendientes ({invitacionesPendientes.length})</h2>
        {invitacionesPendientes.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No tienes invitaciones pendientes por responder.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {invitacionesPendientes.map((item) => {
              const lote = item.lote || {};
              const emergencia = item.emergencia || {};
              
              const totalAportadoOferta = (item.participantes || []).reduce(
                (acc, p) => acc + (p.cantidad_aportada || 0), 
                0
              );
              
              const faltanteOferta = Math.max(0, (lote.cantidad || 0) - totalAportadoOferta);


              const nombresParticipantes = (item.participantes || [])
                .filter(p => p.ong_id !== Number(currentOngId) && (p.cantidad_aportada !== null || p.es_lider))
                .map(p => obtenerNombreOng(p.ong_id))
                .join(', ');
              
              return (
                <div 
                  key={item.oferta_id} 
                  style={{ border: '1px solid var(--border)', padding: '1.2rem', borderRadius: '8px', backgroundColor: 'var(--surface)' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                      <span style={{ backgroundColor: 'var(--surface-raised)', border: '1px solid var(--border)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold', display: 'inline-block', marginBottom: '0.5rem' }}>
                        ¡Te invitaron a colaborar!
                      </span>
                      <h3 style={{ margin: '0 0 0.4rem 0' }}>{lote.tipoRecurso || 'Recurso'}</h3>
                      <p style={{ margin: '0 0 0.5rem 0', color: 'var(--muted)' }}>{emergencia.zonaAfectada || 'Emergencia'}</p>
                      <p style={{ margin: 0, color: 'var(--muted)', fontSize: '0.9rem' }}>
                        Lote requerido: <strong>{lote.cantidad}</strong> | 
                        Aportado: <strong>{totalAportadoOferta}</strong> | 
                        Faltan: <strong style={{ color: 'var(--danger)' }}>{faltanteOferta}</strong>
                      </p>
                      <p style={{ margin: '0 0 0.3rem 0', fontSize: '0.9rem', color: 'var(--muted)' }}>
                        ONGs Participantes: <strong>{nombresParticipantes || 'Ninguna aún'}</strong>
                      </p>
                    </div>
                  </div>

                  <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                      <label htmlFor={`cantidad-aporte-${item.oferta_id}`} style={{ display: 'block', fontWeight: '600', fontSize: '0.85rem', marginBottom: '0.2rem' }}>
                        ¿Cuántas unidades puedes aportar? (Máx: {faltanteOferta}):
                      </label>
                      <input 
                        className="form-control"
                        id={`cantidad-aporte-${item.oferta_id}`}
                        type="number"
                        min="1"
                        max={faltanteOferta}
                        placeholder={`Máximo ${faltanteOferta}`}
                        value={cantidadesAportadas[item.oferta_id] || ''}
                        onChange={(e) => handleCantidadChange(item.oferta_id, e.target.value)}
                        style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={() => handleResponderInvitacion(item.oferta_id, true, faltanteOferta)}
                        disabled={submittingId === item.oferta_id}
                        style={{ padding: '0.6rem 1.2rem', backgroundColor: 'var(--primary)', color: 'var(--on-primary)', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: submittingId === item.oferta_id ? 'not-allowed' : 'pointer' }}
                      >
                        {submittingId === item.oferta_id ? 'Guardando...' : 'Aceptar Invitacion y Enviar Oferta'}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleResponderInvitacion(item.oferta_id, false, faltanteOferta)}
                        disabled={submittingId === item.oferta_id}
                        style={{ padding: '0.6rem 1.2rem', backgroundColor: 'var(--surface-raised)', color: 'var(--ink)', border: '1px solid var(--border)', borderRadius: '4px', fontWeight: 'bold', cursor: submittingId === item.oferta_id ? 'not-allowed' : 'pointer' }}
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
      <section style={{ marginTop: '3rem' }}>
        <h2 style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>Consorcios donde Participo ({misConsorcios.length})</h2>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                      <h3 style={{ margin: '0 0 0.4rem 0' }}>{lote.tipoRecurso}</h3>
                      <p style={{ margin: '0 0 0.5rem 0', color: 'var(--muted)' }}>{emergencia.zonaAfectada}</p>
                      <p style={{ margin: '0 0 0.3rem 0', fontSize: '0.9rem' }}>
                        Rol: <strong>{item.es_lider ? 'ONG Líder 👑' : 'Colaborador 🤝'}</strong>
                      </p>
                      <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)' }}>
                        Mi Aporte Confirmado: <strong>{item.mi_aporte || 0} unidades</strong>
                      </p>
                    </div>
                  </div>

                  {/* Lista de Participantes del Consorcio */}
                  <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: 'var(--surface-raised)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <p style={{ margin: '0 0 0.4rem 0', fontWeight: '600', fontSize: '0.85rem' }}>Participantes del Consorcio:</p>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.85rem', color: 'var(--muted)' }}>
                      {(item.participantes || []).map((p, idx) => (
                        <li key={idx} style={{ marginBottom: '0.2rem' }}>
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