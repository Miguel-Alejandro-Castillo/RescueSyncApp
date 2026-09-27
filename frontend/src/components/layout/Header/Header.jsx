import { NavLink } from "react-router-dom";
import Brand from "../Brand";
import styles from "./Header.module.css";
import { useState } from "react";
import { logout } from "../../../services/authService";
export default function Header() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function handleLogout() {
    if (pending) return;
    setPending(true);
    setError("");
    try {
      await logout();
    } catch (error) {
      setError(error.message);
    } finally {
      setPending(false);
    }
  }
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Brand showIcon={false} />
        <nav className={styles.nav} aria-label="Navegación principal">
          <NavLink to="/dashboard">Inicio</NavLink>
          <NavLink to="/emergencias/nueva">Emergencias</NavLink>
          <NavLink to="/lotes/nuevo">Lotes y convocatorias</NavLink>
        </nav>
        <button className={styles.login} type="button" onClick={handleLogout} disabled={pending}>
          {pending ? "Cerrando sesión…" : "Cerrar sesión"}
        </button>
        {error && <p className="field-error" role="alert">{error}</p>}
      </div>
    </header>
  );
}
