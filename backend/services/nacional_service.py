import os
import httpx


class NacionalService:
    """Delegar validación y cobertura al Sistema Nacional, sin reservar recursos."""

    def __init__(self, client=None):
        self.client = client or httpx.AsyncClient(
            base_url=os.environ['BONITA_ENGINE_URL'].rstrip('/') + '/',
            timeout=15,
        )

    async def _authenticate(self):
        if self.client.cookies.get('X-Bonita-API-Token'):
            return
        response = await self.client.post('loginservice', data={
            'username': os.environ['BONITA_USER'],
            'password': os.environ['BONITA_PASSWORD'],
            'redirect': 'false',
        })
        response.raise_for_status()
        if not self.client.cookies.get('X-Bonita-API-Token'):
            raise ValueError('Bonita no devolvió una sesión válida para la extensión nacional')

    async def _request(self, method, path, **kwargs):
        await self._authenticate()
        response = await self.client.request(
            method, 'API/extension/sistemaNacional/' + path,
            headers={'X-Bonita-API-Token': self.client.cookies['X-Bonita-API-Token']},
            **kwargs,
        )
        response.raise_for_status()
        return response.json()['data']

    async def get(self, path, **kwargs):
        return await self._request('GET', path, **kwargs)

    async def recursos(self):
        return await self.get('recursos')

    async def validar_ofertas(self, solicitud):
        return await self._request('POST', 'validaciones/ofertas', json=solicitud)

    async def inventario(self, cuit):
        ongs = await self.get('ongs', params={'cuit': cuit})
        if not ongs:
            return None
        if len(ongs) != 1:
            raise ValueError('El CUIT no identifica una única ONG nacional')
        return await self.get(f"ongs/{ongs[0]['id']}/recursos")

    async def close(self):
        await self.client.aclose()


async def get_nacional_service():
    service = NacionalService()
    try:
        yield service
    finally:
        await service.close()
