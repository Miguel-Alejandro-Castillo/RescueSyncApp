// src/routes/index.js
import { Router } from 'express';
import ongRoutes from './ong.routes.js';
import systemRoutes from './system.routes.js';
import authRoutes from './auth.routes.js';

const router = Router();

/*
  Rutas de la API
*/

router.use('/auth', authRoutes);
router.use('/ongs', ongRoutes);

export default router;