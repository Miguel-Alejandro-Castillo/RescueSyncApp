import express from 'express';
import { getAllCategorias } from '../controllers/categoria.controller.js';

const router = express.Router();

// Definir las rutas para las categorías aquí

/**
 * @swagger
 * tags:
 *   name: Categorias
 *   description: API endpoints for managing Categorias
 */
/**
 * @openapi
 * /api/v1/categorias:
 *   get:
 *     summary: Obtener todas las categorías
 *     tags: [Categorias]
 *     responses:
 *       200:
 *         description: Lista de categorías obtenida correctamente
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 type: object
 *                 properties:
 *                   id:
 *                     type: integer
 *                     example: 1
 *                   nombre:
 *                     type: string
 *                     example: "Rescate"
 *       500:
 *         description: Error interno del servidor
 */
router.get('/', getAllCategorias);

export default router;