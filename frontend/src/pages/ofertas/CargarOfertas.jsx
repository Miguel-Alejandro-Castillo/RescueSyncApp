import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './CargarOfertas.module.css';

export default function CargarOfertas() {
  const [emergencias, setEmergencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const navigate = useNavigate();

  const fetchEmergencias = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:3000/api/rescue/ofertas/emergencias-disponibles');
      if (!response.ok) throw new Error('Error al obtener emergencias disponibles');
      const data = await response.json();
      setEmergencias(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmergencias();
  }, []);

  if (loading) return <div className={styles.page}>Cargando emergencias...</div>;
  if (error) return <div className={styles.page}>Error: {error}</div>;

  return (
    <div className={styles.page}>
      <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        
        {}
        <div className={styles.card}>
          <div className={styles.cardBody}>
            <h1 className={styles.title}> Ofertas Emergencias</h1>
            <p style={{ color: '#5b6e8a' }}>
              S
            </p>
          </div>
        </div>

        {}
        {emergencias.length === 0 ? (
          <div className={styles.card}>
            <div className={styles.cardBody}>
              <p>No hay emergencias activas con lotes disponibles en este momento.</p>
            </div>
          </div>
        ) : (
          emergencias.map((item) => {
            const emergencia = item.emergencia || item;
            const lotes = item.lotes_disponibles || item.lotes || [];

            return (
              <div key={emergencia.id} className={styles.card}>
                <div className={styles.cardBody}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    
                    <div>
                      <h2 className={styles.title} style={{ marginBottom: '0.4rem' }}>
                         {emergencia.zonaAfectada}
                      </h2>
                      <p style={{ color: '#4a5568', margin: 0 }}>{emergencia.descripcionInicial}</p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <span style={{
                        padding: '0.4rem 0.8rem',
                        borderRadius: '0.6rem',
                        fontWeight: 'bold',
                        fontSize: '0.85rem',
                        backgroundColor: emergencia.nivelGravedad === 'Critica' ? '#ffe5e5' : '#fff3cd',
                        color: emergencia.nivelGravedad === 'Critica' ? '#d90429' : '#856404'
                      }}>
                        Gravedad: {emergencia.nivelGravedad}
                      </span>

                      {/* BOTÓN NAVEGAR A PÁGINA DE LOTES */}
                     <button 
  className={styles.submit}
  onClick={() => navigate(`/emergencias/${emergencia.id}/lotes`)}
>
  Ver lotes disponibles ({lotes.length})
</button>
                    </div>

                  </div>
                </div>
              </div>
            );
          })
        )}

      </div>
    </div>
  );
}