import {
    BrowserRouter,
    Routes,
    Route
} from "react-router-dom";

import Dashboard from "../pages/dashboard/Dashboard";
import AltaEmergencia from "../pages/emergencias/AltaEmergencia";
import AltaLotes from "../pages/lotes/AltaLotes";
import Login from "../pages/auth/Login";

function AppRouter() {

    return (
        <BrowserRouter>

            <Routes>

                <Route
                    path="/"
                    element={<Dashboard />}
                />

                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/dashboard"
                    element={<Dashboard />}
                />

                <Route
                    path="/emergencias/nueva"
                    element={<AltaEmergencia />}
                />

                <Route
                    path="/lotes/nuevo"
                    element={<AltaLotes />}
                />
            </Routes>

        </BrowserRouter>
    );
}

export default AppRouter;
