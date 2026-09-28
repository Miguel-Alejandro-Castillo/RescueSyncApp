import { NavLink } from "react-router-dom";
import Brand from "../Brand";
import styles from "./Header.module.css";
import { useState } from "react";
import { logout, getSessionRoles, getSessionMemberships } from "../../../services/authService";
import { ACTIONS, canAccess } from "../../../auth/permissions";
import { useSession } from "../../../auth/AuthContext";
export default function Header() {
  const session = useSession();
  const roles = getSessionRoles(session);
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
          {ACTIONS.filter(action => canAccess(getSessionMemberships(session), action.permission)).map(action =>
            <NavLink key={action.path} to={action.path}>{action.label}</NavLink>
          )}
        </nav>
        <div className={styles.account}>
          <div className={styles.identity}>
            <strong>{session?.username}</strong>
            <span>{roles.length ? roles.join(" · ") : "Sin rol"}</span>
          </div>
        <button className={styles.login} type="button" onClick={handleLogout} disabled={pending}>
          {pending ? "Cerrando sesión…" : "Cerrar sesión"}
        </button>
        </div>
        {error && <p className="field-error" role="alert">{error}</p>}
      </div>
    </header>
  );
}
