import express from 'express';
import { getAllOngs, getOngById, getRecursosOng, createOng } from '../controllers/ong.controller.js';

const router = express.Router();

/**
 * @swagger
 * tags:
 *   name: ONGs
 *   description: API endpoints for managing ONGs
 */
/**
 * @swagger
 * /api/v1/ongs:
 *   get:
 *     summary: Retrieve a list of all ONGs
 *     tags: [ONGs]
 *     parameters:
 *       - in: query
 *         name: cuit
 *         schema:
 *           type: string
 *         description: CUIT de la ONG (mismo formato que el catálogo nacional)
 *     responses:
 *       200:
 *         description: A list of ONGs
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
 *                   razonSocial:
 *                     type: string
 *                     example: ONG Example
 */
router.get('/', getAllOngs);
/**
 * @swagger
 * /api/v1/ongs/{id}/recursos:
 *   get:
 *     summary: Consultar inventario y disponibilidad de una ONG sin reservar recursos
 *     tags: [ONGs]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *           minimum: 1
 *     responses:
 *       200:
 *         description: Datos de la ONG y recursos con cantidadTotal, cantidadComprometida y cantidadDisponible, dentro de data
 *       400:
 *         description: Identificador inválido
 *       404:
 *         description: ONG no encontrada
 */
router.get('/:id/recursos', getRecursosOng);

/**
 * @swagger
 * /api/v1/ongs/{id}:
 *   get:
 *     summary: Retrieve a single ONG by ID
 *     tags: [ONGs]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         example: 1
 *     responses:
 *       200:
 *         description: A single ONG
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 id:
 *                   type: integer
 *                   example: 1
 *                 razonSocial:
 *                   type: string
 *                   example: ONG Example
 *       404:
 *         description: ONG not found
 */
router.get('/:id', getOngById);

/**
 * @swagger
 * /api/v1/ongs:
 *   post:
 *     summary: Create a new ONG
 *     tags: [ONGs]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               razonSocial:
 *                 type: string
 *                 example: ONG Example
 *               descripcion:
 *                 type: string
 *                 example: A description of the ONG
 *               sigla:
 *                 type: string
 *                 example: ONGEX
 *               cuit:
 *                 type: string
 *                 example: 20-12345678-9
 *     responses:
 *       201:
 *         description: ONG created successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 id:
 *                   type: integer
 *                   example: 1
 *                 razonSocial:
 *                   type: string
 *                   example: ONG Example
 *                 descripcion:
 *                   type: string
 *                   example: A description of the ONG
 *                 sigla:
 *                   type: string
 *                   example: ONGEX
 *                 cuit:
 *                   type: string
 *                   example: 20-12345678-9
 */
router.post('/', createOng);

export default router;
