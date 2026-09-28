import { Link } from "react-router-dom";
import styles from "./Dashboard.module.css";
export default function Dashboard() {
  return (
    <>
      <div className="page-heading">
        <h1 id="actions-title">Accesos rápidos</h1>
      </div>

      <section aria-labelledby="actions-title">
        <div className={styles.grid}>
          <Link to="/emergencias/nueva" className={styles.action}>


            <h3>Registrar una emergencia</h3>
            <p>
              Indicá la zona afectada, el nivel de gravedad y la situación
              inicial.
            </p>
          </Link>
          <Link to="/lotes/nuevo" className={styles.action}>

            <h3>Organizar lotes de ayuda</h3>
            <p>
              Definí los recursos necesarios y la duración de la convocatoria
              para ONGs.
            </p>
          </Link>
        </div>
      </section>
    </>
  );
}
