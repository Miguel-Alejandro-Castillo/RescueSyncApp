import os
from fastapi import Depends, HTTPException
from services.bonita_service import BonitaService
from dependencies.jwt_auth import get_current_user


async def get_bonita_service(
    current_user=Depends(get_current_user)
):
    bonita = BonitaService()

    bonita.j_session = current_user["bonita_auth"]
    bonita.api_token = current_user["bonita_token"]

    try:
        yield bonita
    finally:
        await bonita.close()

async def get_bonita_service_cuenta_servicio():
    """Sesión de Bonita con la cuenta de servicio (BONITA_USER/BONITA_PASSWORD).

    El perfil "User" de Bonita no puede consultar procesos ni tareas, ni borrar casos por REST,
    y los actores del proceso están mapeados a la cuenta de servicio. La identidad y el rol del
    usuario se validan igualmente en la API (JWT + RBAC).
    """
    bonita = BonitaService()
    try:
        login = await bonita.login(os.getenv("BONITA_USER"), os.getenv("BONITA_PASSWORD"))
        if not login["success"]:
            raise HTTPException(status_code=502, detail="No se pudo autenticar la cuenta de servicio de Bonita")
        yield bonita
    finally:
        await bonita.close()
