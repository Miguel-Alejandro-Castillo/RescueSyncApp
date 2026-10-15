import styles from './ResultadoValidacion.module.css';

export default function ResultadoValidacion({ resultado, fecha }) {
  if (!resultado || resultado.error) return <div className={styles.pending} role="status">
    <strong>{resultado?.error ? 'No se pudo completar la consulta' : 'Todavía no se verificaron los recursos'}</strong>
    <p>{resultado?.error || 'La consulta se realiza cuando termina la ventana de urgencia.'}</p>
  </div>;
  const participantes = resultado.participantes || [];
  return <div className={styles.result}>
    {resultado.motivo && <p>{resultado.motivo}</p>}
    {resultado.cantidad_aceptada != null && <p><strong>El coordinador aceptó {resultado.cantidad_aceptada} unidades con cobertura parcial.</strong></p>}
    {participantes.length > 0 && <div className={styles.scroll}>
      <table className={styles.table}>
        <caption className="visually-hidden">Disponibilidad de los recursos ofertados por cada ONG</caption>
        <thead><tr><th scope="col">Organización</th><th scope="col" className={styles.quantity}>Ofrece</th>
          <th scope="col">Disponibilidad</th></tr></thead>
        <tbody>{participantes.map(p => <tr key={p.participante_id}>
          <td><span className={styles.ong}>{p.ong_nombre || 'Organización sin identificar'}</span></td>
          <td className={styles.quantity}>{p.cantidad_ofertada}</td>
          <td><span className={p.valida ? styles.check : styles.shortage}>
            {p.valida ? 'Recursos suficientes' : 'Disponibilidad insuficiente'}
          </span></td>
        </tr>)}</tbody>
      </table>
    </div>}
    {fecha && <p className={styles.date}>Inventario consultado el {new Date(fecha).toLocaleString('es-AR')}</p>}
  </div>;
}
