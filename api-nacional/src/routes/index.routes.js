// src/routes/index.js
import { Router } from 'express';
import ongRoutes from './ong.routes.js';
import systemRoutes from './system.routes.js';
import authRoutes from './auth.routes.js';
import validacionRoutes from './validacion.routes.js';
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

const router = Router();

/*
  Rutas de la API
*/

router.use('/auth', authRoutes);
router.use('/ongs', ongRoutes);
router.use('/validaciones', validacionRoutes);
/**
 * @swagger
 * /api/v1/recursos:
 *   get:
 *     summary: Consultar el catálogo nacional de recursos y sus códigos
 *     responses:
 *       200:
 *         description: Lista de recursos y categorías dentro de data
 */
router.get('/recursos', async (req, res) => {
  const recursos = await prisma.recurso.findMany({
    include: { categoria: true }, orderBy: { codigo: 'asc' },
  });
  return ApiResponse.ok(res, recursos);
});

export default router;
