import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllCategorias = async (req, res) => {
    const categorias = await prisma.categoria.findMany({ orderBy: { codigo: 'asc' }});
    return ApiResponse.ok(res, categorias);
};