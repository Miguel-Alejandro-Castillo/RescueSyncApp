import asyncio
from datetime import time
import os
from clients.http_client import HttpClient
import asyncio
import time

class BonitaService:

    # definir constantes para la autenticación de la api de bonita
    API_TOKEN_HEADER = "X-Bonita-API-Token"
    COOKIE_JSESSIONID = "JSESSIONID"

    def __init__(self):
        base_url = os.getenv(
            "BONITA_ENGINE_URL"
        )
        self.api_path = os.getenv(
            "BONITA_ENGINE_API_PATH"
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
        print("cookies", self.http_client.client.cookies)
        print("Auth headers:", self._auth_headers())
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
    
    async def iniciar_proceso(self, process_id: str, contract: dict = {}):
        response = await self.http_client.post(
            f"{self.api_path}/process/{process_id}/instantiation",
            headers=self._auth_headers(),
            json = contract # A JSON object matching process contract.
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
        print(f"Obteniendo tareas humanas para el caseId {caseId}")

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

    # Completa una tarea humana específica por su ID
    async def completar_tarea_humana(self, task_id: str, contract: dict = {}):
        await self.http_client.post(
            f"{self.api_path}/userTask/{task_id}/execution",
            headers=self._auth_headers(),
            json = contract, # A JSON object matching task contract.
            params = {
                "assign": True
            }
        )
        # retorna un HTTP 204, no devuelve nada, solo completa la tarea humana

    # Devuelve un listado de todos los usuarios disponibles
    async def obtener_usuarios(self):
        response = await self.http_client.get(
            f"{self.api_path}/user",
            headers=self._auth_headers(),
            params = {
                "p": 0 # (Required) index of the page to display
            } 
        )
        return response.json()
    
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
    
    async def close(self):
        """Cierra las conexiones del cliente HTTP subyacente."""
        await self.http_client.close()
