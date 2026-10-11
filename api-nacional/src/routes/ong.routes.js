import express from 'express';
import { getAllOngs, getOngById } from '../controllers/ong.controller.js';

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

export default router;
