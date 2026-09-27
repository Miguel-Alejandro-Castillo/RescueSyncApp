// Servicio temporal: reemplazar por la llamada HTTP cuando esté disponible.
export const crearLotes = async () =>
  new Promise((resolve) => {
    setTimeout(() => resolve({ success: true }), 500);
  });
