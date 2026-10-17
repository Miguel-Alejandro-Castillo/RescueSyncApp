import asyncio
import os
from clients.http_client import HttpClient
import time
import httpx
from fastapi import HTTPException

class BonitaService:

    # definir constantes para la autenticación de la api de bonita
    API_TOKEN_HEADER = "X-Bonita-API-Token"
    COOKIE_JSESSIONID = "JSESSIONID"

    def __init__(self):
        base_url = os.getenv("BONITA_ENGINE_URL")
        self.api_path = os.getenv("BONITA_ENGINE_API_PATH")

        if not base_url:
            raise RuntimeError(
                "La variable BONITA_ENGINE_URL no está configurada"
            )

        if not self.api_path:
            raise RuntimeError(
                "La variable BONITA_ENGINE_API_PATH no está configurada"
            )

        self.http_client = HttpClient(base_url=base_url)

    # Obtiene el token de autenticación de Bonita desde las cookies del cliente HTTP
    @property
    def api_token(self):
        return self.http_client.client.cookies.get(self.API_TOKEN_HEADER)

    # setter de api_token (actualiza la cookie correspondiente en el cliente HTTP)
    @api_token.setter
    def api_token(self, value):
        self.http_client.client.cookies.set(self.API_TOKEN_HEADER, value)

    @property
    def j_session(self):
        return self.http_client.client.cookies.get(self.COOKIE_JSESSIONID)

    # setter de j_session (actualiza la cookie correspondiente en el cliente HTTP)
    @j_session.setter
    def j_session(self, value):
        self.http_client.client.cookies.set(self.COOKIE_JSESSIONID, value)

    def _auth_headers(self):
        token = self.api_token
        if not token:
            # si no hay token, no se incluyen los encabezados de autenticación en la solicitud HTTP
            return {}
        return {
            self.API_TOKEN_HEADER: token
        }

    # Login en Bonita y obtiene el token de autenticación
    async def login(self, username: str, password: str):
        await self.http_client.post(
            "/loginservice",
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            data = {
                "username": username,
                "password": password,
                "redirect": "false",
                "redirectURL": ""
            }
        )

        jsessionid = self.j_session
        api_token = self.api_token

        return {
            "success": bool(jsessionid and api_token),
            "sessionId": jsessionid,
            "token": api_token
        }

    # devuelve un array de objetos con la información personalizada del usuario
    async def get_custom_user_info(self, user_id: str):
        response = await self.http_client.get(
            f"/API/customuserinfo/user",
            params = {
                "p": 0, # (Required) index of the page to display
                "f": f"userId={user_id}"
            },
            headers=self._auth_headers()
        )
        return response.json()

    # Obtiene la información personalizada de un usuario específico por su ID y el nombre de la definición
    async def get_custom_user_info_by_user_id_and_definition_name(self, user_id: str, definition_name: str):
        custom_user_info = await self.get_custom_user_info(user_id)
        for item in custom_user_info:
            # Verifica si el item corresponde a la definición solicitada y tiene un valor asociado
            if item["definitionId"]["name"] == definition_name and item["value"]:
                return item
        return None

    async def get_user_info(self, username: str):
        # A regular user can read their own identity, but cannot search all users.
        session = await self.http_client.get(
            "/API/system/session/unusedId",
            headers=self._auth_headers(),
        )
        user_id = session.json()["user_id"]
        response = await self.http_client.get(
            f"/API/identity/user/{user_id}",
            headers=self._auth_headers(),
        )
        user_info = response.json()
        if user_info["userName"] != username:
            raise ValueError("La sesión de Bonita no corresponde al usuario solicitado")
        return user_info

    # Devuelve los memberships(grupo + rol) de un usuario específico por su ID
    async def get_memberships_by_user_id(self, user_id: str):
        response = await self.http_client.get(
            "/API/identity/membership",
            headers=self._auth_headers(),
            params = {
                "p": 0, # (Required) index of the page to display
                "f": f"user_id={user_id}"
            }
        )
        return response.json()

    async def get_group_by_id(self, group_id: str):
        response = await self.http_client.get(
            f"/API/identity/group/{group_id}",
            headers=self._auth_headers()
        )
        return response.json()

    async def get_role_by_id(self, role_id: str):
        response = await self.http_client.get(
            f"/API/identity/role/{role_id}",
            headers=self._auth_headers()
        )
        return response.json()

    async def get_role_by_name(self, role_name: str):
        response = await self.http_client.get(
            "/API/identity/role",
            headers=self._auth_headers(),
            params = {
                "p": 0, # (Required) index of the page to display
                "f": f"name={role_name}"
            }
        )
        roles = response.json()
        return roles[0] if roles else None

    # Logout de Bonita y limpieza de cookies del cliente HTTP
    async def logout(self):
        await self.http_client.post(
            "/logoutservice",
            headers=self._auth_headers(),
            params = {
                "redirect": "false"
            }
        )
        # limpiar las cookies del cliente HTTP después del logout
        self.http_client.client.cookies.clear()
        return {"success": not bool(self.api_token)}

    # Devuelve un listado de todos los procesos disponibles en Bonita
    async def obtener_procesos(self):
        response = await self.http_client.get(
            f"{self.api_path}/process",
            headers=self._auth_headers(),
            params = {
                "p": 0 # (Required) index of the page to display
            }  # se puede agregar paginación u otros parámetros según sea necesario
        )
        return response.json()

    # Devuelve un listado de procesos que coinciden con el nombre proporcionado
    async def obtener_procesos_por_nombre(self, process_name: str):
        response = await self.http_client.get(
            f"{self.api_path}/process",
            headers=self._auth_headers(),
            params = {
                "p": 0, # (Required) index of the page to display
                "f": f"name={process_name}"
            }
        )
        return response.json()

    async def obtener_proceso_por_nombre(self, process_name: str):
        procesos = await self.obtener_procesos_por_nombre(process_name)
        return procesos[0] if procesos else None

    # Devuelve un proceso específico por su ID
    async def obtener_proceso_por_id(self, process_id: str):
        response = await self.http_client.get(
            f"{self.api_path}/process/{process_id}",
            headers=self._auth_headers()
        )
        return response.json()

    async def iniciar_proceso(self, process_id: str, contract: dict | None = None):
        response = await self.http_client.post(
            f"{self.api_path}/process/{process_id}/instantiation",
            headers=self._auth_headers(),
            json = contract or {} # A JSON object matching process contract.
        )
        return response.json()

    # Devuelve el contrato de un proceso específico
    async def obtener_contrato_proceso(self, process_id: str):
        response = await self.http_client.get(
            f"{self.api_path}/process/{process_id}/contract",
            headers=self._auth_headers()
        )
        return response.json()

    # Devuelve un caso específico por su ID
    async def obtener_caso_por_id(self, case_id: str):
        response = await self.http_client.get(
            f"{self.api_path}/case/{case_id}",
            headers=self._auth_headers()
        )
        return response.json()

    # elimina un caso específico por su ID, si es exitoso devuelve un HTTP 200 con body vacío
    async def borrar_caso_por_id(self, case_id: str):
        await self.http_client.delete(
            f"{self.api_path}/case/{case_id}",
            headers=self._auth_headers()
        )

    # Devuelve un listado de todas las tareas activas por caso
    async def obtener_tareas_por_caso(self, caseId: str):
        params = [
            ("p", 0),
            ("f", f"caseId={caseId}"),
            ("f", "state=ready")
        ]
        response = await self.http_client.get(
            f"{self.api_path}/task",
            headers=self._auth_headers(),
            params = params
        )
        return response.json()

    # Devuelve un listado de todas las tareas humanas activas por caso
    async def obtener_tareas_humanas_por_caso(self, caseId: str):
        params = [
            ("p", 0),
            ("f", f"caseId={caseId}"),
            ("f", "state=ready")
        ]
        response = await self.http_client.get(
            f"{self.api_path}/humanTask",
            headers=self._auth_headers(),
            params = params
        )

        return response.json()

    # Devuelve la primera tarea humana activa para un caso específico, o None si no hay tareas disponibles.
    async def obtener_tarea_humana_por_caso(self, caseId: str):
        tareas = await self.obtener_tareas_humanas_por_caso(caseId)
        return tareas[0] if tareas else None

    # Completa una tarea humana específica por su ID
    async def resolver_accion_coordinador(self, case_id: str, accion: str):
        if accion not in {"PUBLICAR_CONVOCATORIA", "GENERAR_LOTES", "ACEPTAR_OFERTAS"}:
            raise ValueError("Acción de coordinador desconocida")
        tareas = await self.obtener_tareas_humanas_por_caso(case_id)
        tarea = next((t for t in tareas if t["name"].strip() == "Evaluar acciones a tomar"), None)
        if not tarea:
            raise HTTPException(409, "El caso no está esperando la decisión del coordinador en Bonita.")
        await self.completar_tarea_humana(tarea["id"], {"accionSeleccionadaInput": accion})

    async def completar_tarea_humana(self, task_id: str, contract: dict | None = None):
        await self.http_client.post(
            f"{self.api_path}/userTask/{task_id}/execution",
            headers=self._auth_headers(),
            json = contract or {}, # A JSON object matching task contract.
            params = {
                "assign": True
            }
        )
        # retorna un HTTP 204, no devuelve nada, solo completa la tarea humana

    # Devuelve un listado de todos los usuarios disponibles
    async def obtener_usuarios(self):
        response = await self.http_client.get(
            "/API/identity/user",
            headers=self._auth_headers(),
            params = {
                "p": 0, # (Required) index of the page to display
                "f": "enabled=true" # (Optional) filter to only include enabled users
            }
        )
        return response.json()

    async def obtener_usuarios_por_rol(self, role_name: str):
        role = await self.get_role_by_name(role_name)
        if not role:
            return []

        response = []
        usuarios = await self.obtener_usuarios()
        for usuario in usuarios:
             memberships = await self.get_memberships_by_user_id(usuario["id"])
             for membership in memberships:
                 if membership["role_id"] == role["id"]:
                     response.append(usuario)
        return response

    # Espera hasta que aparezcan tareas humanas en estado 'ready' para un caso específico o hasta que se agote el tiempo de espera.
    async def esperar_tareas_humanas_por_caso(
        self,
        caseId: str,
        timeout_segundos: int = 20,
        intervalo_ms: int = 200
    ):
        inicio = time.monotonic()

        while True:

            tareas = await self.obtener_tareas_humanas_por_caso(caseId)

            if tareas:
                return tareas

            transcurrido = time.monotonic() - inicio

            if transcurrido >= timeout_segundos:
                raise TimeoutError(
                    f"No aparecieron tareas para el caso {caseId} "
                    f"en {timeout_segundos} segundos"
                )

            await asyncio.sleep(
                intervalo_ms / 1000
            )

    async def esperar_tarea_humana_por_caso(
        self,
        caseId: str,
        timeout_segundos: int = 20,
        intervalo_ms: int = 200
    ):
        tareas = await self.esperar_tareas_humanas_por_caso(caseId, timeout_segundos, intervalo_ms)
        return tareas[0] if tareas else None

    # Establece una variable de proceso de un caso específica en Bonita BPM. Devuelve un 200 OK sin cuerpo.
    # Parámetros:
    # - caseId: ID del caso en Bonita BPM.
    # - variable_name: Nombre de la variable a establecer.
    # - tipo_variable: Tipo de la variable en Java (e.g., "java.lang.Long").
    # - variable_value: Valor de la variable a establecer.
    # Java type for the variable (e.g., "java.lang.Long")
    async def set_case_variable(self, caseId: str, variable_name: str, tipo_variable: str, variable_value):
        await self.http_client.put(
            f"{self.api_path}/caseVariable/{caseId}/{variable_name}",
            headers=self._auth_headers(),
            json = {
                "type": tipo_variable,
                "value": variable_value
            }
        )

    async def close(self):
        """Cierra las conexiones del cliente HTTP subyacente."""
        await self.http_client.close()

    async def obtener_cuit_ong(self, user_id: int):
        page = 0
        while True:
            response = await self.http_client.get(
                "/API/customuserinfo/user",
                headers=self._auth_headers(),
                params={"p": page, "c": 100, "f": f"userId={user_id}"},
            )
            values = response.json()
            for item in values:
                if item.get("definitionId", {}).get("name") == "cuitONG":
                    return (item.get("value") or "").strip() or None
            if len(values) < 100:
                return None
            page += 1


class BonitaValidacionService(BonitaService):
    """Autentica al consultar identidades; permite guardar y reintentar fallas."""
    async def obtener_cuit_ong(self, user_id: int):
        if not self.api_token:
            auth = await self.login(os.getenv('BONITA_USER'), os.getenv('BONITA_PASSWORD'))
            if not auth['success']:
                raise ValueError('No se pudo autenticar la cuenta de servicio de Bonita')
        return await super().obtener_cuit_ong(user_id)


async def get_bonita_validacion_service():
    service = BonitaValidacionService()
    try:
        yield service
    finally:
        await service.close()
