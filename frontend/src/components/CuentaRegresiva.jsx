import { useEffect, useState } from 'react';
import { calcularRestanteMs, formatearRestante, parsearFechaUTC } from '../utils/cuentaRegresiva';

// reloj que descuenta solo en el navegador hasta fechaLimite
export default function CuentaRegresiva({ fechaLimite, onFinalizar }) {
  const limite = parsearFechaUTC(fechaLimite);
  const [restanteMs, setRestanteMs] = useState(() => (limite ? calcularRestanteMs(limite) : 0));

  useEffect(() => {
    if (!limite) return undefined;
    const tick = () => setRestanteMs(calcularRestanteMs(limite));
    tick();
    const intervalo = setInterval(tick, 1000);
    return () => clearInterval(intervalo);
  }, [fechaLimite]);

  const cerrada = restanteMs === 0;

  useEffect(() => {
    if (limite && cerrada) onFinalizar?.();
  }, [cerrada]);
  if (!limite) return null;

  return (
    <span
      role="timer"
      aria-live="off"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4rem',
        padding: '0.4rem 0.8rem',
        borderRadius: '0.6rem',
        fontWeight: 'bold',
        fontSize: '0.85rem',
        fontVariantNumeric: 'tabular-nums',
        backgroundColor: cerrada ? '#e9ecef' : '#ffe5e5',
        color: cerrada ? '#6c757d' : '#d90429'
      }}
    >
      {cerrada ? 'Convocatoria cerrada' : `⏱ Cierra en ${formatearRestante(restanteMs)}`}
    </span>
  );
}
