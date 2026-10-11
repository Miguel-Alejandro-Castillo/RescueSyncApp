import express from 'express';
import cors from 'cors';
import apiRouter from './routes/index.routes.js';
import systemRouter from './routes/system.routes.js';
import jwt from './middlewares/jwt.middleware.js';
import notFound from './middlewares/not-found.middleware.js';
import errorHandler from './middlewares/error-handler.middleware.js';
import swaggerUi from 'swagger-ui-express';
import { swaggerSpec } from './config/swagger.js';

// -------------------------
// Configuración de Express
// -------------------------

const app = express();

app.use(express.json());
app.use(cors());

// uncomment if JWT validation should be enforced globally
//app.use(jwt);

// Definición del API path global en un solo lugar
const apiPath = process.env.API_PATH;
app.use(apiPath, apiRouter);

/* Rutas del sistema / & /health */
app.use(systemRouter);

app.use(
  "/api-docs",
  swaggerUi.serve,
  swaggerUi.setup(swaggerSpec)
);

app.use(express.json({
  limit: "10mb"
}));

/* Middlewares globales */

// Middleware para manejar rutas no encontradas
app.use(notFound);

// Manejador de errores global...
app.use(errorHandler);

export default app;