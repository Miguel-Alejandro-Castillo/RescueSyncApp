import express from 'express';
import { getAllOngs, createOng, getOngById, addRecurso, getRecursosOng } from '../controllers/ong.controller.js';

const router = express.Router();

/**
 * @swagger
 * tags:
 *   name: ONGs
 *   description: Consulta y alta de organizaciones no gubernamentales
 */
/**
 * @swagger
 * /api/v1/ongs:
 *   get:
 *     summary: Listar ONG
 *     description: Devuelve todas las ONG, o filtra por CUIT cuando se informa el parámetro.
 *     tags: [ONGs]
 *     parameters:
 *       - in: query
 *         name: cuit
 *         schema:
 *           type: string
 *         description: CUIT de la ONG (mismo formato que el catálogo nacional)
 *     responses:
 *       200:
 *         description: Lista de ONG
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
 *                       razonSocial: { type: string, example: ONG de prueba }
 *                       cuit: { type: string, example: "20-12345678-9" }
 *       401:
 *         description: Token ausente, inválido o vencido
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
 *         description: Datos de la ONG y su inventario, con cantidades totales, reservadas y disponibles
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     id: { type: integer, example: 1 }
 *                     cuit: { type: string, example: "20-12345678-9" }
 *                     razonSocial: { type: string, example: ONG Ejemplo }
 *                     estado: { type: string, example: HABILITADA }
 *                     recursos:
 *                       type: array
 *                       items:
 *                         type: object
 *                         properties:
 *                           codigo: { type: string, example: MED-GEN }
 *                           nombre: { type: string, example: Médico clínico }
 *                           cantidadTotal: { type: integer, example: 20 }
 *                           cantidadReservada: { type: integer, example: 5 }
 *                           cantidadDisponible: { type: integer, example: 15 }
 *       400:
 *         description: Identificador inválido
 *       404:
 *         description: ONG no encontrada
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.get('/:id/recursos', getRecursosOng);

/**
 * @swagger
 * /api/v1/ongs/{id}:
 *   get:
 *     summary: Obtener una ONG por identificador
 *     description: Busca una ONG por su identificador nacional.
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
 *         description: Datos de una ONG
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     id: { type: integer, example: 1 }
 *                     razonSocial: { type: string, example: ONG de prueba }
 *                     descripcion: { type: string, nullable: true }
 *                     sigla: { type: string, example: ONGPRUEBA }
 *                     cuit: { type: string, example: "20-12345678-9" }
 *                     estado: { type: string, example: HABILITADA }
 *       404:
 *         description: ONG no encontrada
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.get('/:id', getOngById);

/**
 * @swagger
 * /api/v1/ongs:
 *   post:
 *     security:
 *       - BearerAuth: []
 *     summary: Crear una ONG
 *     description: Registra una ONG y devuelve sus datos.
 *     tags: [ONGs]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [razonSocial, sigla, cuit]
 *             properties:
 *               razonSocial:
 *                 type: string
 *                 example: ONG de prueba
 *               descripcion:
 *                 type: string
 *                 example: Organización de asistencia y rescate
 *               sigla:
 *                 type: string
 *                 example: ONGPRUEBA
 *               cuit:
 *                 type: string
 *                 example: 20-12345678-9
 *     responses:
 *       201:
 *         description: ONG creada correctamente
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     id: { type: integer, example: 1 }
 *                     razonSocial: { type: string, example: ONG de prueba }
 *                     descripcion: { type: string, nullable: true }
 *                     sigla: { type: string, example: ONGPRUEBA }
 *                     cuit: { type: string, example: "20-12345678-9" }
 *                     estado: { type: string, example: HABILITADA }
 *       401:
 *         description: Token ausente, inválido o vencido
 */
router.post('/', createOng);

/**
 * @swagger
 * /api/v1/ongs/{id}/recursos:
 *   put:
 *     security:
 *       - BearerAuth: []
 *     summary: Agregar un recurso a una ONG
 *     description: Asocia un recurso existente a una ONG.
 *     tags: [ONGs]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         example: 1
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [recursoId, cantidadTotal]
 *             properties:
 *               recursoId:
 *                 type: integer
 *                 example: 1
 *               cantidadTotal:
 *                 type: integer
 *                 example: 10
 *     responses:
 *       200:
 *         description: Recurso agregado correctamente
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: object
 *                   properties:
 *                     ongId: { type: integer, example: 1 }
 *                     recursoId: { type: integer, example: 1 }
 *                     cantidadTotal: { type: integer, example: 10 }
 *                     cantidadReservada: { type: integer, example: 0 }
 *       404:
 *         description: Recurso no encontrado
 *       400:
 *         description: Solicitud incorrecta
 *       401:
 *         description: Token ausente, inválido o vencido
 *       500:
 *         description: Error interno del servidor
 */
router.put('/:id/recursos', addRecurso);

export default router;
