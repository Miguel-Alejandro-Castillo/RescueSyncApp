import {
    BrowserRouter,
    Routes,
    Route
} from "react-router-dom";

import Home from "../pages/Home";
import AltaEmergencia from "../pages/AltaEmergencia";

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

            </Routes>

        </BrowserRouter>
    );
}

export default AppRouter;