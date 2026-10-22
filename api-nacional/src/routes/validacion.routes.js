import { Router } from 'express';
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';
import { reservarOfertas, liberarReserva } from '../services/reservas.service.js';

const router = Router();

router.post('/ofertas', async (req, res) => {
  const resultado = await reservarOfertas(prisma, req.body);
  return ApiResponse.ok(res, resultado);
});

router.post('/reservas/liberar', async (req, res) => {
  return ApiResponse.ok(res, await liberarReserva(prisma, req.body));
});

export default router;
