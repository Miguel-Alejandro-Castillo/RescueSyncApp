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
      cantidadReservada: item.cantidadReservada,
      cantidadDisponible: Math.max(0, item.cantidadTotal - item.cantidadReservada),
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

export const createOng = async (req, res) => {

  const { razonSocial, descripcion, sigla, cuit } = req.body;

  if (!razonSocial)
    return ApiResponse.badRequest(res, 'RAZON_SOCIAL_REQUIRED', 'Razon social es requerida');
  if (!cuit)
    return ApiResponse.badRequest(res, 'CUIT_REQUIRED', 'CUIT es requerido');
  if (!sigla)
    return ApiResponse.badRequest(res, 'SIGLA_REQUIRED', 'Sigla es requerida');

  const ong = await prisma.ong.create({
    data: {
      razonSocial,
      descripcion,
      sigla,
      cuit
    }
  });

  return ApiResponse.created(res, ong);
};

export const addRecurso = async (req, res) => { 

  const { id } = req.params;

  const { recursoId, cantidadTotal } = req.body;

  if (!id)
    return ApiResponse.badRequest(res, 'ONG_ID_REQUIRED', 'El ID de la ONG es requerido');

  if (!recursoId)
    return ApiResponse.badRequest(res, 'RECURSO_ID_REQUIRED', 'El ID del recurso es requerido');

  if (!cantidadTotal)
    return ApiResponse.badRequest(res, 'CANTIDAD_TOTAL_REQUIRED', 'La cantidad total es requerida');

  // BUSCAR LA ONG
  const ong = await prisma.ong.findUnique({
    where: { id: Number(id) }
  });
  if (!ong) return ApiResponse.notFound(res, 'ONG_NOT_FOUND', 'ONG no encontrada');

  // BUSCAR EL RECURSO
  const recurso = await prisma.recurso.findUnique({
    where: { id: Number(recursoId) }
  });
  if (!recurso) return ApiResponse.notFound(res, 'RECURSO_NOT_FOUND', 'Recurso no encontrado');

  const ongRecurso = await prisma.ongRecurso.create({
    data: {
      ongId: Number(id),
      recursoId: Number(recursoId),
      cantidadTotal: Number(cantidadTotal)
    }
  });

  return ApiResponse.ok(res, ongRecurso);
};
