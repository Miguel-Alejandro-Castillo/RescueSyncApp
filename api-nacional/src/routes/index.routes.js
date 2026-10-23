// src/routes/index.js
import { Router } from 'express';
import ongRoutes from './ong.routes.js';
import authRoutes from './auth.routes.js';
import validacionRoutes from './validacion.routes.js';
import recursoRoutes from './recurso.routes.js';
import categoriaRoutes from './categoria.routes.js';
import verifyJWT from '../middlewares/jwt.middleware.js';

const router = Router();

/*
  Rutas de la API
*/

router.use('/auth', authRoutes);
router.use('/ongs', verifyJWT, ongRoutes);
router.use('/recursos', verifyJWT, recursoRoutes);
router.use('/categorias', verifyJWT, categoriaRoutes);
router.use('/validaciones', verifyJWT, validacionRoutes);

export default router;
