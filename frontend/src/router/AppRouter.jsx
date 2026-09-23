import {
    BrowserRouter,
    Routes,
    Route
} from "react-router-dom";

import Home from "../pages/Home";
import AltaEmergencia from "../pages/AltaEmergencia";
import AltaLotes from "../pages/AltaLotes";

function AppRouter() {

    return (
        <BrowserRouter>

            <Routes>

                <Route
                    path="/"
                    element={<Home />}
                />

                <Route
                    path="/emergencias/nueva"
                    element={<AltaEmergencia />}
                />

                <Route
                    path="lotes/nuevo"
                    element={<AltaLotes />}
                />
            </Routes>

        </BrowserRouter>
    );
}

export default AppRouter;
