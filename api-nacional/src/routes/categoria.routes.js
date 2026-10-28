import express from 'express';
import { getAllCategorias, createCategoria, getCategoriaById } from '../controllers/categoria.controller.js';

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

/**
 * @swagger
 * /api/v1/categorias:
 *   post:
 *     summary: Crear una nueva categoría
 *     description: Crea una nueva categoría en el catálogo de categorías.
 *     tags: [Categorias]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               codigo: { type: string, example: RES }
 *               nombre: { type: string, example: Rescate }
 *     responses:
 *       201:
 *         description: Categoría creada correctamente
 *       400:
 *         description: Solicitud inválida
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.post('/', createCategoria);


/**
 * @swagger
 * /api/v1/categorias/{id}:
 *   get:
 *     summary: Obtener una categoría por ID
 *     description: Devuelve una categoría específica según su ID.
 *     tags: [Categorias]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: ID de la categoría
 *     responses:
 *       200:
 *         description: Categoría obtenida correctamente
 *       401:
 *         description: Token ausente, inválido o vencido
 *       404:
 *         description: Categoría no encontrada
 *       500:
 *         description: Error interno del servidor
 */
router.get('/:id', getCategoriaById);

export default router;
