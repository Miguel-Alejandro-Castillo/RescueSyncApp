import { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Outlet,
  Navigate,
  useLocation,
  Link,
} from "react-router-dom";
import Dashboard from "../pages/dashboard/Dashboard";
import AltaEmergencia from "../pages/emergencias/AltaEmergencia";
import MisEmergencias from "../pages/emergencias/MisEmergencias";
import VerLotes from "../pages/emergencias/VerLotes";
import AdjudicarOfertas from "../pages/emergencias/AdjudicarOfertas";
import AltaLotes from "../pages/lotes/AltaLotes";
import Login from "../pages/auth/Login";
import Header from "../components/layout/Header/Header";
import Footer from "../components/layout/Footer/Footer";
import CargarOfertas from "../pages/ofertas/CargarOfertas";
import DetalleLotes from "../pages/ofertas/DetalleLotes";
import MisOfertas from '../pages/ofertas/MisOfertas';
import { useSession } from "../auth/AuthContext";
import RequirePermission from "../auth/RequirePermission";
import OfertasConsorcio from '../pages/ofertas/OfertasConsorcio';
import OfertasInvalidas from '../pages/ofertas/OfertasInvalidas';
import ValidacionOfertas from '../pages/ofertas/ValidacionOfertas';
import Monitoreo from '../pages/monitoreo/Monitoreo';
function RequireSession() {
  const session = useSession();
  const location = useLocation();
  return session ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
}
function Layout() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <Header />
      <main id="contenido" className="main-content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        {import.meta.env.DEV && <Route path="/validacion-ofertas/demo" element={<Layout />}>
          <Route index element={<ValidacionOfertas demo />} />
        </Route>}
        <Route element={<RequireSession />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/emergencias/nueva" element={<RequirePermission permission="emergencias.crear"><AltaEmergencia /></RequirePermission>} />
            <Route path="/emergencias/propias" element={<RequirePermission permission="emergencias.ver_propias"><MisEmergencias /></RequirePermission>} />
            <Route path="/emergencias/propias/:id/lotes" element={<RequirePermission permission="emergencias.ver_lotes"><VerLotes /></RequirePermission>} />
            <Route path="/emergencias/propias/:id/lotes/:idLote/adjudicar-ofertas" element={<RequirePermission permission="emergencias.adjudicar_ofertas"><AdjudicarOfertas /></RequirePermission>} />
            <Route path="/lotes/nuevo" element={<RequirePermission permission="lotes.crear"><AltaLotes /></RequirePermission>} />
            <Route path="/ofertas" element={<RequirePermission permission="ofertas.crear"><CargarOfertas /></RequirePermission>} />
            <Route path="/emergencias/:id/lotes" element={<RequirePermission permission="ofertas.crear"><DetalleLotes /></RequirePermission>} />
            <Route path="/ofertas/misofertas" element={<RequirePermission permission="ofertas.ver_propias"><MisOfertas /></RequirePermission>} />
            <Route path="/ofertas-consorcio" element={<RequirePermission permission="ofertas.ver_propias"><OfertasConsorcio /></RequirePermission>} />
            <Route path="/ofertas-invalidas" element={<RequirePermission permission="ofertas.ver_invalidas"><OfertasInvalidas /></RequirePermission>} />
            <Route path="/validacion-ofertas" element={<RequirePermission permission="ofertas.ver_validacion"><ValidacionOfertas /></RequirePermission>} />
            <Route path="/monitoreo" element={<RequirePermission permission="monitoreo.ver"><Monitoreo /></RequirePermission>} />
            <Route
              path="*"
              element={
                <div className="panel">
                  <h1>Página no encontrada</h1>
                  <p>La dirección que ingresaste no está disponible.</p>
                  <Link className="btn btn-primary" to="/dashboard">
                    Volver al inicio
                  </Link>
                </div>
              }
            />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
