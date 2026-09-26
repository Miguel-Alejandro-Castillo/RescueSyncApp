import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// Importación de estilos y javascript  de Bootstrap
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

// Global styles, variables de CSS y reset inicial de estilos 
import './assets/css/globals.css';
import './assets/css/reset.css';
import './assets/css/variables.css';

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
