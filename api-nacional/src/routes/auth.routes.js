import express from 'express';
import { login, logout } from '../controllers/auth.controller.js';
import verifyJWT from '../middlewares/jwt.middleware.js';

const router = express.Router();

/**
 * @swagger
 * tags:
 *   name: Auth
 *   description: Inicio y cierre de sesión
 */
/**
 * @swagger
 * /api/v1/auth/login:
 *   post:
 *     summary: Iniciar sesión
 *     description: Autentica un usuario y devuelve un JWT.
 *     tags: [Auth]
 *     security: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [username, password]
 *             properties:
 *               username: { type: string, example: user }
 *               password: { type: string, format: password, example: user123 }
 *     responses:
 *       200:
 *         description: Token emitido
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     access_token: { type: string, description: JWT para enviar como Bearer }
 *                     token_type: { type: string, example: Bearer }
 *                     expires_in: { type: integer, description: Duración del token en segundos }
 *       401:
 *         description: Credenciales incorrectas
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error:
 *                 code: INVALID_CREDENTIALS
 *                 message: Usuario o contraseña incorrectos
 */
router.post('/login', login);

/**
 * @swagger
 * /api/v1/auth/logout:
 *   post:
 *     summary: Cerrar sesión
 *     description: Requiere un JWT válido. Responde sin contenido.
 *     tags: [Auth]
 *     responses:
 *       204:
 *         description: Sesión cerrada
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.post('/logout', verifyJWT, logout);

export default router;
