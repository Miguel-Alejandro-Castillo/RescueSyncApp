import { Link } from 'react-router-dom';
import { useSession } from './AuthContext';
import { canAccess } from './permissions';
import { getSessionMemberships } from '../services/authService';

export default function RequirePermission({ permission, children }) {
  const session = useSession();
  if (canAccess(getSessionMemberships(session), permission)) return children;
  return <section className="panel">
    <h1>Acceso restringido</h1>
    <p>Tu sesión actual no tiene acceso a esta función.</p>
    <Link className="btn btn-outline-secondary" to="/dashboard">Volver al inicio</Link>
  </section>;
}
