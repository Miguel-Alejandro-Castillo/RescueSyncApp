import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import apiRouter from './routes/index.routes.js';
import systemRouter from './routes/system.routes.js';
import notFound from './middlewares/not-found.middleware.js';
import errorHandler from './middlewares/error-handler.middleware.js';
import swaggerUi from 'swagger-ui-express';
import { swaggerSpec } from './config/swagger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.resolve(__dirname, '../public');

// -------------------------
// Configuración de Express
// -------------------------

const app = express();

app.use(express.json());
app.use(cors());

app.use(
  "/api-docs",
  swaggerUi.serve,
  swaggerUi.setup(swaggerSpec, {
    swaggerOptions: {
      tagsSorter: (a, b) => a.localeCompare(b)
    }
  })
);

// Panel web de administración de ONGs y stock (API Nacional)
app.use('/admin', express.static(publicDir));
app.get('/admin', (_req, res) => {
  res.sendFile(path.join(publicDir, 'admin.html'));
});

// Swagger queda público; el resto de las rutas requiere un JWT válido.
// El login es la única ruta pública dentro de la API. 
// Ademas, el health check  también sera público.

// Definición del API path global en un solo lugar
const apiPath = process.env.API_PATH;
app.use(apiPath, apiRouter);

/* Rutas del sistema / & /health */
app.use(systemRouter);

// Limite de tamaño para las solicitudes JSON
app.use(express.json({
  limit: "10mb"
}));

/* Middlewares globales */

// Middleware para manejar rutas no encontradas
app.use(notFound);

// Manejador de errores global...
app.use(errorHandler);

export default app;
