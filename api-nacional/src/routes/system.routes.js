import express from 'express';

const router = express.Router();

/**
 * @swagger
 * tags:
 *   name: Sistema
 *   description: Estado del servicio
 */
/**
 * @swagger
 * /:
 *   get:
 *     summary: Comprobar que la API Nacional responde
 *     tags: [Sistema]
 *     responses:
 *       200:
 *         description: Mensaje de estado del servicio
 *         content:
 *           text/html:
 *             schema: { type: string, example: API REST del Sistema Nacional de Gestión de Recursos y Riesgos en funcionamiento }
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.get("/", (req, res) => {
  console.log("Received request for /");
  res.send("API REST del Sistema Nacional de Gestión de Recursos y Riesgos en funcionamiento");
});

/**
 * @swagger
 * /health:
 *   get:
 *     summary: Consultar el estado de la API y Redis
 *     tags: [Sistema]
 *     responses:
 *       200:
 *         description: Estado del servicio y conexión Redis
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 status: { type: string, example: ok }
 *                 service: { type: string, example: api-nacional }
 *                 redis: { type: string, enum: [connected, disconnected], example: connected }
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.get("/health", async (req, res) => {
  const redis = req.app.locals.redis;
  let redisStatus = "disconnected";

  if (redis?.isOpen) {
    await redis.ping();
    redisStatus = "connected";
  }

  res.json({
    status: "ok",
    service: "api-nacional",
    redis: redisStatus
  });
});

export default router;
