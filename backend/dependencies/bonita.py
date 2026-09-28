from fastapi import Depends
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