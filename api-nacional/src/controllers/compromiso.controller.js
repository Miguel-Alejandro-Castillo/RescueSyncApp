
import prisma from '../config/prisma.js';
import ApiResponse from '../utils/api-response.js';

export const createCompromiso = async (req, res) => {
    const { detalleAdjudicacionRef, cantidad, ongId, recursoId } = req.body;

    if(!detalleAdjudicacionRef)
        return ApiResponse.error(res, 'DETALLE_ADJUDICACION_REF_REQUIRED', 'detalleAdjudicacionRef es requerido', 400);
    if(!cantidad)
        return ApiResponse.error(res, 'CANTIDAD_REQUIRED', 'cantidad es requerido', 400);
    if(!ongId)
        return ApiResponse.error(res, 'ONG_ID_REQUIRED', 'ongId es requerido', 400);
    if(!recursoId)
        return ApiResponse.error(res, 'RECURSO_ID_REQUIRED', 'recursoId es requerido', 400);

    // existe de ongId
    const ong = await prisma.ong.findUnique({
        where: { id: ongId }
    });
    if(!ong)
        return ApiResponse.error(res, 'ONG_NOT_FOUND', 'Ong no encontrada', 404);

    // existe de recursoId
    const recurso = await prisma.recurso.findUnique({
        where: { id: recursoId }
    });
    if(!recurso)
        return ApiResponse.error(res, 'RECURSO_NOT_FOUND', 'Recurso no encontrado', 404);

    // Validar si existe el OngRecurso
    const ongRecurso = await prisma.ongRecurso.findUnique({
        where: {
            ongId_recursoId: {
                ongId,
                recursoId
            }
        }
    });
    if(!ongRecurso)
        return ApiResponse.error(res, 'ONG_RECURSO_NOT_FOUND', 'el recurso de la ONG no existe', 404);

    const compromiso = await prisma.compromiso.create({
        data: {
            detalleAdjudicacionRef,
            cantidad,
            ongId,
            recursoId
        }
    });
    return ApiResponse.created(res, compromiso, 201);
};

export const getAllCompromisos = async (req, res) => {
    const compromisos = await prisma.compromiso.findMany();
    return ApiResponse.ok(res, compromisos);
};
