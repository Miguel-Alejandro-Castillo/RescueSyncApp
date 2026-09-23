export const crearLotes = async (data) => {
    console.log("Simulando envío de lotes de necesidades al backend:", data);
    
    // Simula una respuesta exitosa de red para probar la interfaz
    return new Promise((resolve) => {
        setTimeout(() => {
            alert("¡Lotes de necesidades publicados exitosamente! (Simulado)");
            resolve({ success: true, message: "Lotes creados exitosamente" });
        }, 500);
    });
};
