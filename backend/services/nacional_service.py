import os
import httpx


class NacionalService:
    """Consultas de inventario. Nunca modifica ni reserva recursos."""

    def __init__(self, client=None):
        self.client = client or httpx.AsyncClient(
            base_url=os.getenv('NACIONAL_API_URL', 'http://nacional:4000/api/v1').rstrip('/') + '/',
            timeout=15,
        )

    async def get(self, path, **kwargs):
        response = await self.client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()['data']

    async def recursos(self):
        return await self.get('recursos')

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
