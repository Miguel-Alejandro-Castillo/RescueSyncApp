
import { Router } from 'express';
import { createCompromiso, getAllCompromisos } from '../controllers/compromiso.controller.js';
const router = Router();

// Las rutas documentadas son relativas al prefijo de montaje de este router.
/**
 * @swagger
 * /api/v1/compromisos:
 *   post:
 *     summary: Crear un compromiso
 *     description: Registra un compromiso de una cantidad de recursos de una ONG para una adjudicación.
 *     operationId: createCompromiso
 *     tags: [Compromisos]
 *     security:
 *       - BearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - detalleAdjudicacionRef
 *               - cantidad
 *               - ongId
 *               - recursoId
 *             properties:
 *               detalleAdjudicacionRef:
 *                 type: integer
 *                 minimum: 1
 *                 description: Identificador del detalle de adjudicación en el sistema de origen.
 *                 example: 101
 *               cantidad:
 *                 type: integer
 *                 minimum: 1
 *                 description: Cantidad de unidades comprometidas.
 *                 example: 10
 *               ongId:
 *                 type: integer
 *                 minimum: 1
 *                 description: Identificador de la ONG que aporta el recurso.
 *                 example: 7
 *               recursoId:
 *                 type: integer
 *                 minimum: 1
 *                 description: Identificador del recurso comprometido.
 *                 example: 3
 *           example:
 *             detalleAdjudicacionRef: 101
 *             cantidad: 10
 *             ongId: 7
 *             recursoId: 3
 *     responses:
 *       201:
 *         description: Compromiso creado correctamente.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     id: { type: integer, example: 1 }
 *                     detalleAdjudicacionRef: { type: integer, example: 101 }
 *                     cantidad: { type: integer, example: 10 }
 *                     estado: { type: string, enum: [ACTIVO, LIBERADO], example: ACTIVO }
 *                     fechaCompromiso: { type: string, format: date-time, example: "2026-10-23T22:00:00.000Z" }
 *                     fechaLiberacion: { type: string, format: date-time, nullable: true, example: null }
 *                     ongId: { type: integer, example: 7 }
 *                     recursoId: { type: integer, example: 3 }
 *       400:
 *         description: Faltan datos obligatorios o tienen un valor inválido.
 *         content:
 *           application/json:
 *             example:
 *               error:
 *                 code: DETALLE_ADJUDICACION_REF_REQUIRED
 *                 message: detalleAdjudicacionRef es requerido
 *       401:
 *         description: Token ausente, inválido o vencido.
 *       404:
 *         description: La ONG o el recurso indicado no existe.
 *         content:
 *           application/json:
 *             examples:
 *               ongNoEncontrada:
 *                 value:
 *                   error:
 *                     code: ONG_NOT_FOUND
 *                     message: Ong no encontrada
 *               recursoNoEncontrado:
 *                 value:
 *                   error:
 *                     code: RECURSO_NOT_FOUND
 *                     message: Recurso no encontrado
 *       500:
 *         description: Error interno al crear el compromiso.
 */
router.post('/', createCompromiso);

/**
 * @swagger
 * /api/v1/compromisos:
 *   get:
 *     summary: Obtener todos los compromisos
 *     description: Consulta el listado de compromisos registrados.
 *     operationId: getAllCompromisos
 *     tags: [Compromisos]
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: Consulta de compromisos realizada correctamente.
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
 *                       detalleAdjudicacionRef: { type: integer, example: 101 }
 *                       cantidad: { type: integer, example: 10 }
 *                       estado: { type: string, enum: [ACTIVO, LIBERADO], example: ACTIVO }
 *                       fechaCompromiso: { type: string, format: date-time, example: "2026-10-23T22:00:00.000Z" }
 *                       fechaLiberacion: { type: string, format: date-time, nullable: true, example: null }
 *                       ongId: { type: integer, example: 7 }
 *                       recursoId: { type: integer, example: 3 }
 *       404:
 *         description: La ONG o el recurso indicado no existe.
 *         content:
 *           application/json:
 *             examples:
 *               ongNoEncontrada:
 *                 value:
 *                   error:
 *                     code: ONG_NOT_FOUND
 *                     message: Ong no encontrada
 *               recursoNoEncontrado:
 *                 value:
 *                   error:
 *                     code: RECURSO_NOT_FOUND
 *                     message: Recurso no encontrado
 *               ongRecursoNoEncontrado:
 *                 value:
 *                   error:
 *                     code: ONG_RECURSO_NOT_FOUND
 *                     message: el recurso de la ONG no existe
 *       401:
 *         description: Token ausente, inválido o vencido.
 */
router.get('/', getAllCompromisos);

export default router;