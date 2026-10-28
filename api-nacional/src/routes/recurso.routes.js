import express from 'express';
import { getAllRecursos, createRecurso, getRecursoById, liberarRecursos } from '../controllers/recurso.controller.js';

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
 *                       descripcion: { type: string, example: Descripción del recurso }
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.get('/', getAllRecursos);

/**
 * @swagger
 * /api/v1/recursos:
 *   post:
 *     tags:
 *       - Recursos
 *     summary: Crear un nuevo recurso
 *     description: Crea un nuevo recurso en el catálogo nacional.
 *     security:
 *       - BearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               codigo:
 *                 type: string
 *                 example: MED-GEN
 *               nombre:
 *                 type: string
 *                 example: Médico clínico
 *               categoriaId:
 *                 type: integer
 *                 example: 1
 *               descripcion:
 *                 type: string
 *                 example: Descripción del recurso
 *     responses:
 *       201:
 *         description: Recurso creado
 *       400:
 *         description: Solicitud incorrecta
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.post('/', createRecurso);

/**
 * @swagger
 * /api/v1/recursos/{id}:
 *   get:
 *     tags:
 *       - Recursos
 *     summary: Obtener un recurso por ID
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: ID del recurso
 *     responses:
 *       200:
 *         description: Recurso encontrado
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 id: { type: integer, example: 1 }
 *                 codigo: { type: string, example: MED-GEN }
 *                 nombre: { type: string, example: Médico clínico }
 *                 categoriaId: { type: integer, example: 1 }
 *                 descripcion: { type: string, example: Descripción del recurso }
 *       404:
 *         description: Recurso no encontrado
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.get('/:id', getRecursoById);

/**
 * @swagger
 * /api/v1/recursos/liberar:
 *   post:
 *     tags:
 *       - Recursos
 *     summary: Liberar recursos comprometidos/reservados de ONGs
 *     description: Decrementa la cantidad reservada en el inventario nacional de las ONGs indicadas al finalizar una emergencia o proyecto.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - recursos
 *             properties:
 *               recursos:
 *                 type: array
 *                 items:
 *                   type: object
 *                   required:
 *                     - cuit
 *                     - descripcion
 *                     - cantidad_adjudicada
 *                   properties:
 *                     cuit:
 *                       type: string
 *                       example: "30-54603392-5"
 *                     descripcion:
 *                       type: string
 *                       example: "Raciones de comida"
 *                     cantidad_adjudicada:
 *                       type: integer
 *                       example: 20
 *     responses:
 *       200:
 *         description: Recursos liberados exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 mensaje:
 *                   type: string
 *                   example: Se liberaron exitosamente 1 recursos asignados.
 *                 data:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       ong: { type: string, example: "Cruz Roja Argentina" }
 *                       cuit: { type: string, example: "30-54603392-5" }
 *                       recurso: { type: string, example: "Raciones de comida" }
 *                       cantidadLiberada: { type: integer, example: 20 }
 *       400:
 *         description: Error de validación, ONG o recurso inexistente, o cantidad superior a la reservada
 *       500:
 *         description: Error interno del servidor
 */
router.post('/liberar', liberarRecursos);

export default router;
