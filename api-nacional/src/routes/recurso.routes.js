import express from 'express';
import { getAllRecursos } from '../controllers/recurso.controller.js';

const router = express.Router();


/**
 * @swagger
 * tags:
 *   name: Recursos
 *   description: API endpoints for managing Recursos
 */
/**
 * @swagger
 * /api/v1/recursos:
 *   get:
 *     tags:
 *       - Recursos
 *     summary: Consultar el catálogo nacional de recursos y sus códigos
 *     responses:
 *       200:
 *         description: Lista de recursos y categorías dentro de data
 */
router.get('/', getAllRecursos);

export default router;