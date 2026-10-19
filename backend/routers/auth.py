from dependencies.bonita import get_bonita_service
from fastapi import APIRouter, HTTPException, Depends
import os
from fastapi import Response
from datetime import datetime, timedelta, timezone
from jose import jwt
from pydantic import BaseModel
from services.bonita_service import BonitaService
from dependencies.jwt_auth import get_current_user
import traceback
import httpx

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tu_clave_secreta_jwt")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

router = APIRouter(prefix="/auth", tags=["auth"])

class UserLogin(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Expuesto en segundos

# No conviene incluir la dependencia de Bonita(get_bonita_service) directamente en el login, se instancia manualmente dentro de la función
@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(user: UserLogin ):
    bonita = BonitaService()
    try:

        # 1.Autenticar contra Bonita
        login_response = await bonita.login(user.username, user.password)

        # 2. Obtener la información del usuario
        user_info = await bonita.get_user_info(username=user.username)

        # 3. Obtener los memberships (grupos/roles)
        memberships = await bonita.get_memberships_by_user(user_info["id"])

        # 4. Expiración del token
        expire_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire_time = datetime.now(timezone.utc) + expire_delta

        # 5. Construir el payload del JWT
        token_data = {
            "sub": user.username,
            "user_id": user_info["id"],
            "firstname": user_info["firstname"],
            "lastname": user_info["lastname"],
            "memberships": memberships,
            "bonita_auth": login_response.get("sessionId"), # cifrar mas adelante
            "bonita_token": login_response.get("token"),    # cifrar mas adelante
            "iat": datetime.now(timezone.utc),
            "exp": expire_time
        }

        # 6. Obtener la información personalizada del usuario con rol representante de ONG por su definición "cuitONG"
        #    Nota: solo los usuarios representantes de ONG deberian tener ese campo custom con un valor no vacío
        #    Si no existe, custom_user_info será None
        #    deberia ser mas explicito con el rol del usuario antes de intentar obtener la información personalizada
        custom_user_info = await bonita.get_custom_user_info_by_user_id_and_definition_name(user_info["id"], "cuitONG") 
        if custom_user_info:
            token_data["cuitONG"] = custom_user_info["value"]

        fastapi_jwt = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": fastapi_jwt,
            "token_type": "bearer",
            "expires_in": int(expire_delta.total_seconds())
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Authentication service error"
        )
    except HTTPException:
        raise
    finally:
        await bonita.close()
   
@router.post("/logout", status_code=204)
async def logout(bonita: BonitaService = Depends(get_bonita_service)):
    try:
        await bonita.logout()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="No se pudo cerrar sesión del usuario")
        raise HTTPException(status_code=500, detail="Error del servicio de autenticación")
    except Exception as e:
            raise HTTPException(status_code=401, detail="No se pudo cerrar sesión del usuario")
    return Response(status_code=204)
