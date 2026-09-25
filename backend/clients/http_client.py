import httpx

class HttpClient:

    def __init__(self, base_url: str, timeout: int = 60):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    # Este método privado se encarga de realizar la solicitud HTTP utilizando el cliente httpx.AsyncClient.
    # Se utiliza internamente por los métodos públicos get, post, put, delete y patch.
    # kwargs incluye cualquier parámetro soportado por httpx.AsyncClient.request(),
    # por ejemplo:
    #   - params: Query string (?page=1)
    #   - headers: Cabeceras HTTP
    #   - cookies: Cookies de la solicitud
    #   - json: Cuerpo JSON
    #   - data: Form data o x-www-form-urlencoded
    #   - files: Archivos multipart/form-data
    #   - auth: Autenticación básica o personalizada
    #   - timeout: Timeout específico para la solicitud
    #   - follow_redirects: Seguir redirecciones automáticamente
    #   - content: Cuerpo de la solicitud como bytes o texto crudo
    async def _request(self, method: str,
                       endpoint: str,
                       **kwargs) -> httpx.Response:
        response = await self.client.request(
            method=method,
            url=endpoint,
            **kwargs
        )
        response.raise_for_status()
        return response
    
    async def get(self, endpoint: str, **kwargs):
        return  await self._request(
            method="GET",
            endpoint=endpoint,
            **kwargs
        )

    async def post(self, endpoint: str, **kwargs):
        return await self._request(
            method="POST",
            endpoint=endpoint,
            **kwargs
        )

    async def put(self, endpoint: str, **kwargs):
        return await self._request(
            method="PUT",
            endpoint=endpoint,
            **kwargs
        )
        
    async def delete(self, endpoint: str, **kwargs):
        return await self._request(
            method="DELETE",
            endpoint=endpoint,
            **kwargs
        )
    
    async def patch(self, endpoint: str, **kwargs):
        return await self._request(
            method="PATCH",
            endpoint=endpoint,
            **kwargs
        )

    async def close(self):
        await self.client.aclose()
