import { NavLink } from "react-router-dom";
import Brand from "../Brand";
import styles from "./Header.module.css";
export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Brand showIcon={false} />
        <nav className={styles.nav} aria-label="Navegación principal">
          <NavLink to="/dashboard">Inicio</NavLink>
          <NavLink to="/emergencias/nueva">Emergencias</NavLink>
          <NavLink to="/lotes/nuevo">Lotes y convocatorias</NavLink>
        </nav>
        <NavLink className={styles.login} to="/login">
          Iniciar sesión ↗
        </NavLink>
      </div>
    </header>
  );
}
