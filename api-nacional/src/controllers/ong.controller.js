import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllOngs = async (req, res) => {

  const ongs = await prisma.ong.findMany({
    where: req.query.cuit ? { cuit: String(req.query.cuit) } : undefined,
    orderBy: {
      id: "asc"
    }
  });

  return ApiResponse.ok(res, ongs);
};

export const getRecursosOng = async (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isSafeInteger(id) || id <= 0) {
    return ApiResponse.badRequest(res, 'INVALID_ONG_ID', 'El ID debe ser un entero positivo');
  }
  const ong = await prisma.ong.findUnique({
    where: { id },
    include: { recursos: { include: { recurso: { include: { categoria: true } } } } },
  });
  if (!ong) return ApiResponse.notFound(res, 'ONG_NOT_FOUND', 'ONG no encontrada');
  return ApiResponse.ok(res, {
    id: ong.id, cuit: ong.cuit, razonSocial: ong.razonSocial, estado: ong.estado,
    recursos: ong.recursos.map(item => ({
      ...item.recurso,
      cantidadTotal: item.cantidadTotal,
      cantidadComprometida: item.cantidadComprometida,
      cantidadDisponible: Math.max(0, item.cantidadTotal - item.cantidadComprometida),
    })),
  });
};

export const getOngById = async (req, res) => {

  const { id } = req.params;

  const ong = await prisma.ong.findUnique({
    where: {
      id: Number(id)
    }
  });

  if (!ong) {
    return ApiResponse.notFound(res, "ONG_NOT_FOUND", 'ONG not found');
  }

  return ApiResponse.ok(res, ong);
};
