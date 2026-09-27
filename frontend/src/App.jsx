import React from "react";
import AppRouter from "./router/AppRouter";
import { AuthProvider } from "./auth/AuthContext";


function App() {
  return <AuthProvider><AppRouter /></AuthProvider>;
}

/*
function App() {
  return (
    <div>
      <h1>RescueSync Frontend ( with hot reload )</h1>
    </div>
  );
}
*/

export default App;
