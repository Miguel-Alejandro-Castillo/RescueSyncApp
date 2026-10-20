
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllRecursos = async (req, res) => {
  const recursos = await prisma.recurso.findMany({
    orderBy: { codigo: 'asc' }
  });
  return ApiResponse.ok(res, recursos);
};