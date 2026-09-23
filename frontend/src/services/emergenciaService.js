export async function crearEmergencia(
    emergencia
) {
    console.log("Creating emergencia:", emergencia);
    const response =
        await fetch(
            "http://localhost:3000/api/emergencias",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify(
                    emergencia
                )
            }
        );

    return await response.json();
}
