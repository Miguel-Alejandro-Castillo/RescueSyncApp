from fastapi import APIRouter, HTTPException, Depends
import os
from fastapi import Response
from datetime import datetime, timedelta, timezone
from jose import jwt
from pydantic import BaseModel
from services.bonita_service import BonitaService
from auth.jwt_auth import get_current_user

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

# Devuelve los memberships(grupo + rol) con name de grupo y rol de un usuario específico por su nombre de usuario
async def get_memberships_by_user(user_info, bonita: BonitaService):
    memberships = await bonita.get_memberships_by_user_id(user_id=user_info["id"])
    print("Memberships fetched for user:", memberships)
    _memberships = []
    for membership in memberships:
        group = await bonita.get_group_by_id(group_id=membership["group_id"])
        role = await bonita.get_role_by_id(role_id=membership["role_id"])

        _memberships.append({
            "group":group["name"],
            "role": role["name"]
        })
    return _memberships

@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(user: UserLogin):
    bonita = BonitaService()
    try:
        print("Attempting login for user:", user.username)
    
        # 1.Autenticar contra Bonita
        login_response = await bonita.login(user.username, user.password)
  
        # 2. Obtener la información del usuario
        user_info = await bonita.get_user_info(username=user.username)
        
        # 3. Obtener los memberships (grupos/roles)
        memberships = await get_memberships_by_user(user_info, bonita)

        # 4. Expiración del token
        expire_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire_time = datetime.now(timezone.utc) + expire_delta

        # 5. Construir el payload del JWT
        token_data = {
            "sub": user.username,
            "user_id": user_info["id"],
            "memberships": memberships,
            "bonita_auth": login_response.get("sessionId"), # cifrar mas adelante
            "bonita_token": login_response.get("token"),    # cifrar mas adelante
            "iat": datetime.now(timezone.utc),
            "exp": expire_time
        }

        print("Token data to be encoded:", token_data)

        fastapi_jwt = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": fastapi_jwt,
            "token_type": "bearer",
            "expires_in": int(expire_delta.total_seconds())
        }
    
    except HTTPException:
        # Re-lanzar excepciones HTTP explícitas (ej. 401)
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="No se pudo autenticar el usuario")
    finally:
        await bonita.close()
   
@router.post("/logout", status_code=204)
async def logout(current_user= Depends(get_current_user)):
    bonita = BonitaService()
    try:
        bonita.api_token = current_user["bonita_token"]
        bonita.j_session = current_user["bonita_auth"]
        await bonita.logout()
    except Exception as e:
            raise HTTPException(status_code=401, detail="No se pudo cerrar sesión del usuario")
    finally:
        await bonita.http_client.close()
    return Response(status_code=204)