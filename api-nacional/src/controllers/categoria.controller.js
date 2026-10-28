import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllCategorias = async (req, res) => {
    const categorias = await prisma.categoria.findMany({ orderBy: { codigo: 'asc' }});
    return ApiResponse.ok(res, categorias);
};

export const createCategoria = async (req, res) => {
    const { codigo, nombre, descripcion } = req.body;
    if (!codigo)
        return ApiResponse.badRequest(res, 'CODIGO_REQUIRED', 'Código es requerido');
    if (!nombre)
        return ApiResponse.badRequest(res, 'NOMBRE_REQUIRED', 'Nombre es requerido');

    const categoria = await prisma.categoria.create({
        data: { codigo, nombre, descripcion }
    });
    return ApiResponse.created(res, categoria);
};

export const getCategoriaById = async (req, res) => {
    const { id } = req.params;
    const categoria = await prisma.categoria.findUnique({
        where: { id: Number(id) }
    });

    if (!categoria)
        return ApiResponse.notFound(res, 'CATEGORIA_NOT_FOUND', 'Categoría no encontrada');

    return ApiResponse.ok(res, categoria);
};
