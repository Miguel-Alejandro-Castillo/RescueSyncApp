import { Router } from 'express';
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';
import { validarEmergencia } from '../services/validacion.service.js';

const router = Router();

/**
 * @swagger
 * /api/v1/validaciones/ofertas:
 *   post:
 *     summary: Validar ofertas y calcular la cobertura de todos los lotes sin reservar stock
 *     description: Cada oferta se consulta independientemente; representantes del mismo CUIT comparten inventario dentro de una oferta. La cobertura combina ofertas con recursos suficientes y cantidades parciales aceptadas.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [emergencia_id, lotes]
 *             properties:
 *               emergencia_id: {type: integer, minimum: 1}
 *               lotes:
 *                 type: array
 *                 minItems: 1
 *                 items:
 *                   type: object
 *                   required: [lote_id, cantidad_requerida, ofertas]
 *                   properties:
 *                     lote_id: {type: integer, minimum: 1}
 *                     recurso_codigo: {type: string, nullable: true}
 *                     cantidad_requerida: {type: integer, minimum: 1}
 *                     ofertas:
 *                       type: array
 *                       items:
 *                         type: object
 *                         required: [oferta_id, participantes]
 *                         properties:
 *                           oferta_id: {type: integer, minimum: 1}
 *                           cantidad_aceptada: {type: integer, minimum: 0}
 *                           participantes:
 *                             type: array
 *                             items:
 *                               type: object
 *                               required: [participante_id, ong_id, cantidad_ofertada]
 *                               properties:
 *                                 participante_id: {type: integer, minimum: 1}
 *                                 ong_id: {type: integer, minimum: 1, description: Referencia del representante en RescueSync; la identidad nacional se resuelve exclusivamente por CUIT}
 *                                 cuit: {type: string, nullable: true}
 *                                 cantidad_ofertada: {type: integer, minimum: 0}
 *     responses:
 *       200:
 *         description: Resultado dentro de data con completa, cobertura_suficiente, cobertura_por_lote, conteos de ofertas y resultados por oferta. Una vinculación faltante deja la consulta pendiente; no implica falta de stock.
 *       400:
 *         description: Estructura, identificadores o cantidades inválidos
 *       500:
 *         description: No se pudo consultar el inventario; no utilizar como cobertura insuficiente
 */
router.post('/ofertas', async (req, res) => {
  const resultado = await validarEmergencia(req.body, cuits => prisma.ong.findMany({
    where: { cuit: { in: cuits } },
    include: { recursos: { include: { recurso: true } } },
  }));
  return ApiResponse.ok(res, resultado);
});

export default router;
