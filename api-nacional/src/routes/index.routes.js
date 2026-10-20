// src/routes/index.js
import { Router } from 'express';
import ongRoutes from './ong.routes.js';
import systemRoutes from './system.routes.js';
import authRoutes from './auth.routes.js';
import validacionRoutes from './validacion.routes.js';
import recursoRoutes from './recurso.routes.js';
import categoriaRoutes from './categoria.routes.js';
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

const router = Router();

/*
  Rutas de la API
*/

router.use('/auth', authRoutes);
router.use('/ongs', ongRoutes);
router.use('/recursos', recursoRoutes);
router.use('/categorias', categoriaRoutes);
router.use('/validaciones', validacionRoutes);

export default router;
