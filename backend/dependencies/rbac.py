from fastapi import Depends, HTTPException

from dependencies.jwt_auth import get_current_user

OPERADOR_MUNICIPAL = "operador_municipal"
CENTRO_COORDINADOR = "centro_coordinador"
REPRESENTANTE_ONG = "representante_ong"
AUDITOR = "auditor"
DIRECTIVO = "directivo"

AUDITORES = (AUDITOR, DIRECTIVO)


def get_user_roles(current_user: dict) -> set[str]:
    memberships = current_user.get("memberships") or []
    return {
        membership["role"]["name"]
        for membership in memberships
        if isinstance(membership, dict) and isinstance(membership.get("role"), dict)
    }


def require_roles(*roles: str):
    allowed = set(roles)

    async def checker(current_user=Depends(get_current_user)):
        if not get_user_roles(current_user) & allowed:
            raise HTTPException(
                status_code=403,
                detail="No tenés permiso para realizar esta acción"
            )
        return current_user

    return checker
