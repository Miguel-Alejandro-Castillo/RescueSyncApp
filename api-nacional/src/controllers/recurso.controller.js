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

export const liberarRecursos = async (req, res) => {
  // Acepta tanto { recursos: [...] } como directamente el array [...]
  const items = Array.isArray(req.body) ? req.body : req.body.recursos;

  if (!items || !Array.isArray(items) || items.length === 0) {
    return ApiResponse.badRequest(
      res,
      'Debe proporcionar un array "recursos" con al menos un elemento a liberar.'
    );
  }

  // 1. Validar que cada ítem tenga el formato correcto
  for (let i = 0; i < items.length; i++) {
    const { cuit, descripcion, cantidad_adjudicada } = items[i];
    const cantidad = Number(cantidad_adjudicada);

    if (!cuit || !descripcion || isNaN(cantidad) || cantidad <= 0) {
      return ApiResponse.badRequest(
        res,
        `El ítem en la posición ${i} es inválido. Debe tener cuit, descripcion y cantidad_adjudicada mayor a cero.`
      );
    }
  }

  try {
    // 2. Ejecutar la liberación de TODOS los recursos en una sola transacción atómica
    const resultados = await prisma.$transaction(async (tx) => {
      const liberados = [];

      for (const item of items) {
        const cuitLimpio = item.cuit.trim();
        const descLimpia = item.descripcion.trim();
        const cantidad = Number(item.cantidad_adjudicada);

        // A. Buscar la ONG por CUIT
        const ong = await tx.ong.findUnique({
          where: { cuit: cuitLimpio }
        });

        if (!ong) {
          throw new Error(`No se encontró la ONG con CUIT: '${cuitLimpio}'`);
        }

        // B. Buscar el Recurso por nombre (descripcion)
        const recurso = await tx.recurso.findFirst({
          where: {
            nombre: {
              equals: descLimpia,
              mode: 'insensitive' // No distingue mayúsculas/minúsculas
            }
          }
        });

        if (!recurso) {
          throw new Error(`No se encontró el recurso con nombre: '${descLimpia}'`);
        }

        // C. Buscar la relación en OngRecurso
        const inventario = await tx.ongRecurso.findUnique({
          where: {
            ongId_recursoId: {
              ongId: ong.id,
              recursoId: recurso.id
            }
          }
        });

        if (!inventario) {
          throw new Error(
            `La ONG '${ong.razonSocial}' no tiene asignado el recurso '${recurso.nombre}'.`
          );
        }

        // D. Validar que no se libere más de lo que está reservado
        if (inventario.cantidadReservada < cantidad) {
          throw new Error(
            `No se puede liberar el recurso '${recurso.nombre}' para la ONG '${ong.razonSocial}' porque la cantidad solicitada excede el saldo reservado actual.`
          );
        }

        // E. Decrementar la cantidad reservada
        const inventarioActualizado = await tx.ongRecurso.update({
          where: {
            ongId_recursoId: {
              ongId: ong.id,
              recursoId: recurso.id
            }
          },
          data: {
            cantidadReservada: {
              decrement: cantidad
            }
          }
        });

        liberados.push({
          ong: ong.razonSocial,
          cuit: ong.cuit,
          recurso: recurso.nombre,
          cantidadLiberada: cantidad
        });
      }

      return liberados;
    });

    return ApiResponse.ok(res, {
      mensaje: `Se liberaron exitosamente ${resultados.length} recursos asignados.`,
      data: resultados
    });

  } catch (error) {
    return ApiResponse.badRequest(res, error.message);
  }
};