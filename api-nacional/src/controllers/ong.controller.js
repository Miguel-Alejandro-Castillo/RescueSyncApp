import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const getAllOngs = async (req, res) => {

  const ongs = await prisma.ong.findMany({
    orderBy: {
      id: "asc"
    }
  });

  return ApiResponse.ok(res, ongs);
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