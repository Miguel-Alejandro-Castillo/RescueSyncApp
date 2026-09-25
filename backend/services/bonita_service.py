import os
from clients.http_client import HttpClient

class BonitaService:

    # definir constante X-Bonita-API-Token para los encabezados de autenticación
    API_TOKEN_HEADER = "X-Bonita-API-Token"

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

    def _auth_headers(self):
        token = self.api_token
        if not token:
            # si no hay token, no se incluyen los encabezados de autenticación
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
        # no tiene respuesta, devuelve un 204 No Content
        # por seguridad no deberia devolver la API Key directamente
        # en su lugar, se puede devolver un indicador de éxito
        return {"success": bool(self.api_token)}

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

    # Devuelve un listado de todas las tareas disponibles
    async def obtener_tareas(self):
        response = await self.http_client.get(
            f"{self.api_path}/task",
            headers=self._auth_headers(),
            params = {
                "p": 0 # (Required) index of the page to display
            } 
        )
        return response.json()

    # Completa una tarea específica por su ID
    async def completar_tarea(self, task_id: str):
        response = await self.http_client.post(
            f"{self.api_path}/task/{task_id}/execution",
            headers=self._auth_headers(),
            json = {} # A JSON object matching task contract.
        )
        return response.json()

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