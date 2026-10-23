import { Router } from 'express';
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';
import { reservarOfertas, liberarReserva } from '../services/reservas.service.js';

const router = Router();

/**
 * @swagger
 * tags:
 *   name: Validaciones
 *   description: Validación de ofertas y administración de reservas de recursos
 */
/**
 * @swagger
 * /api/v1/validaciones/ofertas:
 *   post:
 *     summary: Validar ofertas de una emergencia y reservar recursos verificados
 *     description: Evalúa los aportes de cada participante contra la disponibilidad del Sistema Nacional. Si la validación de la emergencia está completa, reserva las cantidades verificadas.
 *     tags: [Validaciones]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [emergencia_id, lotes]
 *             properties:
 *               emergencia_id: { type: integer, minimum: 1, example: 12 }
 *               lotes:
 *                 type: array
 *                 items:
 *                   type: object
 *                   required: [lote_id, cantidad_requerida, ofertas]
 *                   properties:
 *                     lote_id: { type: integer, minimum: 1, example: 31 }
 *                     cantidad_requerida: { type: integer, minimum: 1, example: 30 }
 *                     recurso_nombre: { type: string, example: Medicos }
 *                     tipo_recurso: { type: string, example: Personal }
 *                     ofertas:
 *                       type: array
 *                       items:
 *                         type: object
 *                         required: [oferta_id, participantes]
 *                         properties:
 *                           oferta_id: { type: integer, minimum: 1, example: 81 }
 *                           cantidad_aceptada: { type: integer, minimum: 0, description: Cantidad opcional que se quiere aceptar del total verificado }
 *                           participantes:
 *                             type: array
 *                             items:
 *                               type: object
 *                               required: [participante_id, ong_id, cantidad_ofertada]
 *                               properties:
 *                                 participante_id: { type: integer, minimum: 1, example: 101 }
 *                                 ong_id: { type: integer, minimum: 1, example: 7 }
 *                                 cuit: { type: string, example: "20-12345678-9" }
 *                                 cantidad_ofertada: { type: integer, minimum: 0, example: 10 }
 *           example:
 *             emergencia_id: 12
 *             lotes:
 *               - lote_id: 31
 *                 cantidad_requerida: 30
 *                 recurso_nombre: Medicos
 *                 tipo_recurso: Personal
 *                 ofertas:
 *                   - oferta_id: 81
 *                     participantes:
 *                       - { participante_id: 101, ong_id: 7, cuit: "30-54603392-5", cantidad_ofertada: 10 }
 *                       - { participante_id: 102, ong_id: 8, cuit: "30-63749647-2", cantidad_ofertada: 10 }
 *     responses:
 *       200:
 *         description: Resultado de validación y cobertura por lote
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     emergencia_id: { type: integer, example: 12 }
 *                     completa: { type: boolean, description: Indica si se pudieron validar todas las ofertas }
 *                     cobertura_suficiente: { type: boolean }
 *                     cobertura_por_lote: { type: array, items: { type: object } }
 *                     ofertas_validas: { type: integer }
 *                     ofertas_invalidas: { type: integer }
 *                     ofertas_pendientes: { type: integer }
 *                     resultados: { type: array, items: { type: object } }
 *       400:
 *         description: Solicitud con lotes, ofertas o participantes inválidos
 *       401:
 *         description: Token ausente, inválido o vencido
 *       409:
 *         description: Conflicto de inventario durante la reserva
 */
router.post('/ofertas', async (req, res) => {
  const resultado = await reservarOfertas(prisma, req.body);
  return ApiResponse.ok(res, resultado);
});

/**
 * @swagger
 * /api/v1/validaciones/reservas/liberar:
 *   post:
 *     summary: Liberar recursos reservados por una validación
 *     description: Libera los recursos reservados para cada participante, ONG y recurso. Indicá las cantidades verificadas que se obtuvieron al validar la oferta.
 *     tags: [Validaciones]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [resultados]
 *             properties:
 *               resultados:
 *                 type: array
 *                 items:
 *                   type: object
 *                   required: [resultado_validacion]
 *                   properties:
 *                     resultado_validacion:
 *                       type: object
 *                       required: [participantes]
 *                       properties:
 *                         participantes:
 *                           type: array
 *                           items:
 *                             type: object
 *                             required: [cantidad_verificada]
 *                             properties:
 *                               ong_nacional_id: { type: integer, example: 7 }
 *                               recurso_nacional_id: { type: integer, example: 3 }
 *                               cantidad_verificada: { type: integer, minimum: 0, example: 10 }
 *           example:
 *             resultados:
 *               - resultado_validacion:
 *                   participantes:
 *                     - { ong_nacional_id: 7, recurso_nacional_id: 3, cantidad_verificada: 10 }
 *     responses:
 *       200:
 *         description: Reservas liberadas
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     liberada: { type: boolean, example: true }
 *       400:
 *         description: Detalle de recursos o participantes inválido
 *       401:
 *         description: Token ausente, inválido o vencido
 *       409:
 *         description: Inventario inconsistente al liberar recursos
 */
router.post('/reservas/liberar', async (req, res) => {
  return ApiResponse.ok(res, await liberarReserva(prisma, req.body));
});

export default router;
