import express from 'express';
import { getAllRecursos } from '../controllers/recurso.controller.js';

const router = express.Router();


/**
 * @swagger
 * tags:
 *   name: Recursos
 *   description: Consulta del catálogo nacional de recursos
 */
/**
 * @swagger
 * /api/v1/recursos:
 *   get:
 *     tags:
 *       - Recursos
 *     summary: Consultar el catálogo nacional de recursos y sus códigos
 *     description: Devuelve los recursos ordenados por código.
 *     responses:
 *       200:
 *         description: Lista de recursos
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       id: { type: integer, example: 1 }
 *                       codigo: { type: string, example: MED-GEN }
 *                       nombre: { type: string, example: Médico clínico }
 *                       categoriaId: { type: integer, example: 1 }
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.get('/', getAllRecursos);

export default router;
