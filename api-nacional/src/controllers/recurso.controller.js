import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllRecursos = async (req, res) => {
  const recursos = await prisma.recurso.findMany({
    orderBy: { codigo: 'asc' }
  });
  return ApiResponse.ok(res, recursos);
};

export const createRecurso = async (req, res) => {

    const { codigo, nombre, categoriaId, descripcion } = req.body;
    if (!codigo)
        return ApiResponse.badRequest(res, 'CODIGO_REQUIRED', 'Código es requerido');
    if (!nombre)
        return ApiResponse.badRequest(res, 'NOMBRE_REQUIRED', 'Nombre es requerido');
    if (!categoriaId)
        return ApiResponse.badRequest(res, 'CATEGORIA_ID_REQUIRED', 'Categoria ID es requerido');

    //buscar la categoria por ID
    const categoria = await prisma.categoria.findUnique({
        where: { id: Number(categoriaId) }
    });
    if (!categoria)
        return ApiResponse.badRequest(res, 'CATEGORIA_NOT_FOUND', 'Categoria no encontrada');

    const recurso = await prisma.recurso.create({
        data: { codigo, nombre, categoriaId, descripcion }
    });
    return ApiResponse.created(res, recurso);
};

export const getRecursoById = async (req, res) => {
  const { id } = req.params;
  const recurso = await prisma.recurso.findUnique({
    where: { id: Number(id) }
  });

  if (!recurso)
    return ApiResponse.notFound(res, 'RECURSO_NOT_FOUND', 'Recurso no encontrado');

  return ApiResponse.ok(res, recurso);
};
