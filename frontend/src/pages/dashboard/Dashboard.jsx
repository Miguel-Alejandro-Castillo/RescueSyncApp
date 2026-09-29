import { Link, useLocation } from 'react-router-dom'; 
import styles from './Dashboard.module.css';
import { useSession } from '../../auth/AuthContext';
import { getSessionMemberships } from '../../services/authService';
import { ACTIONS, canAccess, getProfiles } from '../../auth/permissions';

export default function Dashboard() {
  const session = useSession();
  const memberships = getSessionMemberships(session);
  const actions = ACTIONS.filter(action => canAccess(memberships, action.permission));
  const profiles = getProfiles(memberships);


  const location = useLocation();
  const mensajeExito = location.state?.mensajeExito;

  return <>
    {mensajeExito && (
      <div className="notice notice-success" role="status" style={{ marginBottom: '1.5rem' }}>
        <p>{mensajeExito}</p>
      </div>
    )}

    <div className="page-heading"><h1 id="actions-title">Accesos rápidos</h1></div>
    <section aria-labelledby="actions-title">
      <div className={styles.grid}>{actions.map(action =>
        <Link key={action.path} to={action.path} className={styles.action}>
          <h2>{action.title}</h2><p>{action.description}</p>
        </Link>
      )}</div>
      {profiles.length === 0 && <div className="notice">Tu cuenta no tiene un perfil reconocido para ninguna acción.</div>}
    </section>
  </>;
}




