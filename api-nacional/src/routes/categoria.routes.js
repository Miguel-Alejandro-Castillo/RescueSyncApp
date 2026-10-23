import express from 'express';
import { getAllCategorias } from '../controllers/categoria.controller.js';

const router = express.Router();

// Definir las rutas para las categorías aquí

/**
 * @swagger
 * tags:
 *   name: Categorias
 *   description: Consulta del catálogo de categorías
 */
/**
 * @swagger
 * /api/v1/categorias:
 *   get:
 *     summary: Obtener todas las categorías
 *     description: Devuelve las categorías ordenadas por código.
 *     tags: [Categorias]
 *     responses:
 *       200:
 *         description: Lista de categorías obtenida correctamente
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
 *                       codigo: { type: string, example: RES }
 *                       nombre: { type: string, example: Rescate }
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.get('/', getAllCategorias);

export default router;
