"""Genera casos REALES de punta a punta (Bonita + base local) para alimentar el dashboard.

Recorre el proceso usando la propia API de RescueSync (igual que lo haría cada rol desde la
pantalla) y Bonita se entera de cada paso. Así las instancias quedan finalizadas en el motor y
los registros locales son consistentes con ellas.

Uso (con todo el stack levantado y las seeds de la API Nacional cargadas), desde tu PC:
    python seed_casos_finalizados.py --olas 2

Cada ola corre 4 casos en paralelo (uno por recurso, para no pelear por el inventario nacional).
La ventana de urgencia de cada caso dura 4 a 8 minutos, así que una ola tarda unos 10 minutos.
Solo necesita httpx (pip install httpx).
"""
import argparse
import asyncio
import base64
import json
import subprocess
import sys
import time

import httpx

# La consola de Windows usa cp1252 y rompe con acentos/símbolos: forzar UTF-8.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "http://localhost:3000/api/rescue"
BONITA = "http://localhost:8080/bonita"
PASSWORD = "bpm"
MUNICIPAL, COORDINADOR, ONG_1, ONG_2 = "william.jobs", "michael.morrison", "thorsten.hartmann", "thomas.wallis"
BONITA_USER = ("walter.bates", "bpm")

# Ambas ONGs comparten el CUIT 30-70759612-7, cuyo stock disponible en la API Nacional es:
# Agua 50, Bomberos 80, Ladrillos 110, Vehículos 140. Las cantidades quedan por debajo de eso.
# (gravedad, tipo de recurso, recurso, cantidad del lote, aporte ONG 1, aporte ONG 2 o None)
ESCENARIOS = [
    ("alto", "Insumos", "Agua", 40, 40, None),
    ("medio", "Personal", "Bomberos", 60, 40, 20),
    ("bajo", "Materiales", "Ladrillos", 80, 50, 30),
    ("alto", "Transporte", "Vehículos", 100, 60, 40),
]
ZONAS = ["Costa Norte", "Valle Central", "Sierra Sur", "Delta", "Puerto Viejo", "Barrio Los Pinos", "Ribera Oeste", "Alto Verde"]


RESET_INVENTARIO_SQL = """
delete from "ReservaConvocatoria";
update "OngRecurso" o
   set "cantidadReservada" = 50 + 20 * (case c.codigo when 'INS' then 0 when 'PER' then 1 when 'MAT' then 2 else 3 end)
  from "Recurso" r join "Categoria" c on c.id = r."categoriaId"
 where r.id = o."recursoId";
"""


def resetear_inventario():
    """Deja el stock de la API Nacional como lo deja su seed (solo para entornos de prueba)."""
    subprocess.run(["docker", "exec", "api-nacional-db", "psql", "-U", "postgres", "-d", "api_nacional",
                    "-c", RESET_INVENTARIO_SQL], check=True, capture_output=True)
    print("Inventario de la API Nacional restablecido.", flush=True)


def log(caso, mensaje):
    print(f"[{time.strftime('%H:%M:%S')}] caso {caso}: {mensaje}", flush=True)


async def esperar(descripcion, intento, timeout=600, intervalo=5):
    """Repite `intento` (corrutina que devuelve algo verdadero al lograrse) hasta el timeout."""
    limite = time.monotonic() + timeout
    ultimo = None
    while time.monotonic() < limite:
        try:
            resultado = await intento()
            if resultado:
                return resultado
        except httpx.HTTPStatusError as error:
            ultimo = f"{error.response.status_code} {error.response.text[:200]}"
        except httpx.TransportError as error:
            # El servidor cierra las conexiones inactivas (keep-alive): se reintenta.
            ultimo = repr(error)
        await asyncio.sleep(intervalo)
    raise TimeoutError(f"Se agotó el tiempo esperando: {descripcion}. Último error: {ultimo}")


class Cliente:
    """Sesión autenticada de un usuario contra la API de RescueSync."""

    def __init__(self, usuario):
        self.usuario = usuario
        self.http = httpx.AsyncClient(base_url=API, timeout=60)
        self.user_id = None

    async def login(self):
        r = await self.http.post("/auth/login", json={"username": self.usuario, "password": PASSWORD})
        r.raise_for_status()
        token = r.json()["access_token"]
        self.http.headers["Authorization"] = f"Bearer {token}"
        payload = token.split(".")[1]
        self.user_id = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["user_id"]
        return self

    async def request(self, metodo, url, **kwargs):
        r = await self.http.request(metodo, url, **kwargs)
        r.raise_for_status()
        return r.json() if r.content else None


class BonitaAdmin:
    """Solo para comprobar el estado del caso y destrabar la tarea de ejecución si hiciera falta."""

    def __init__(self):
        self.http = httpx.AsyncClient(base_url=BONITA, timeout=60)

    async def login(self):
        r = await self.http.post("/loginservice", data={
            "username": BONITA_USER[0], "password": BONITA_USER[1], "redirect": "false"})
        r.raise_for_status()
        self.http.headers["X-Bonita-API-Token"] = self.http.cookies.get("X-Bonita-API-Token")
        return self

    async def get(self, ruta, **params):
        r = await self.http.get(f"/API/bpm/{ruta}", params=params)
        r.raise_for_status()
        return r.json()

    async def tareas_listas(self, caso_id):
        return await self.get("humanTask", p=0, c=50, f=[f"caseId={caso_id}", "state=ready"])

    async def completar(self, tarea_id):
        r = await self.http.post(f"/API/bpm/userTask/{tarea_id}/execution", params={"assign": "true"}, json={})
        r.raise_for_status()

    async def caso_finalizado(self, caso_id):
        archivados = await self.get("archivedCase", p=0, c=10, f=f"sourceObjectId={caso_id}")
        return any(c.get("state") == "completed" for c in archivados)


async def correr_caso(n, escenario, zona, usuarios, bonita):
    gravedad, tipo, recurso, cantidad, aporte_1, aporte_2 = escenario
    municipal, coordinador, ong_1, ong_2 = usuarios

    emergencia = await municipal.request("POST", "/emergencias", json={
        "zonaAfectada": zona, "nivelGravedad": gravedad, "usuarioCreador": "seed",
        "descripcionInicial": f"Caso de demostración {n} para el dashboard"})
    emergencia_id, caso_bonita = emergencia["id"], emergencia["bonitaCaseId"]
    log(n, f"emergencia {emergencia_id} creada (caso Bonita {caso_bonita}, gravedad {gravedad})")

    lotes = await coordinador.request("POST", "/lotes", json={"emergenciaId": emergencia_id, "lotes": [
        {"tipoRecurso": tipo, "descripcion": recurso, "cantidad": cantidad}]})
    lote_id = lotes[0]["id"]
    log(n, f"lote {lote_id} publicado ({recurso} x{cantidad}); la ventana de urgencia ya corre")

    invitados = [int(ong_2.user_id)] if aporte_2 else []
    oferta = await ong_1.request("POST", "/ofertas/", json={
        "id_lote": lote_id, "cantidad_lider": aporte_1, "invitados": invitados})
    oferta_id = oferta["oferta_id"]
    if aporte_2:
        await ong_2.request("POST", f"/ofertas/{oferta_id}/responder-invitacion", json={
            "aceptar": True, "cantidad_aportada": aporte_2})
    log(n, f"oferta {oferta_id} cargada ({'consorcio' if aporte_2 else 'individual'})")

    async def validada():
        detalle = await coordinador.request("GET", f"/ofertas/{oferta_id}/detalle")
        return detalle if detalle["estado_validacion"] in ("valida", "invalida") else None

    detalle = await esperar("que venza la ventana y se valide la oferta", validada, timeout=900)
    if detalle["estado_validacion"] != "valida":
        raise RuntimeError(f"La oferta {oferta_id} quedó inválida ({detalle['resultado_validacion']}); "
                           "revisá que las seeds de la API Nacional estén cargadas.")
    log(n, "oferta validada por la API Nacional")

    # Se adjudica todo lo ofertado (el lote debe quedar cubierto).
    adjudicacion = [{"detalles": [
        {"participante_id": p["id"], "cantidad_adjudicada": p["cantidad_aportada"]}
        for p in detalle["participantes"] if p["cantidad_aportada"]]}]

    async def adjudicada():
        await municipal.request("POST", f"/ofertas/{lote_id}/adjudicaciones", json=adjudicacion)
        return True

    await esperar("que Bonita habilite la adjudicación", adjudicada, timeout=300)
    log(n, "lote adjudicado")

    for ong in (ong_1, ong_2) if aporte_2 else (ong_1,):
        await ong.request("POST", f"/monitoreo/emergencias/{emergencia_id}/tareas-finalizadas")
    log(n, "las ONGs marcaron sus tareas como finalizadas")

    async def completar_ejecucion():
        """En el proceso 'Ejecutar y finalizar actividades' corre en paralelo con el monitoreo: hay que cerrarla."""
        for tarea in await bonita.tareas_listas(caso_bonita):
            nombre = " ".join(tarea["name"].split())
            if nombre == "Ejecutar y finalizar actividades de ayuda":
                await bonita.completar(tarea["id"])
            if nombre == "Monitorear la ejecucion":
                return True
        return False

    await esperar("la tarea 'Monitorear la ejecucion' en Bonita", completar_ejecucion, timeout=300, intervalo=3)

    async def finalizado():
        await coordinador.request("POST", f"/monitoreo/emergencias/{emergencia_id}/finalizar")
        return True

    await esperar("finalizar el monitoreo", finalizado, timeout=120, intervalo=3)

    async def caso_cerrado():
        await completar_ejecucion()
        return await bonita.caso_finalizado(caso_bonita)

    await esperar("que Bonita archive el caso como finalizado", caso_cerrado, timeout=180, intervalo=3)
    log(n, "FINALIZADO en Bonita y en la base local")


async def main(olas, reset_inventario):
    usuarios = [await Cliente(u).login() for u in (MUNICIPAL, COORDINADOR, ONG_1, ONG_2)]
    bonita = await BonitaAdmin().login()
    numero = 0
    for ola in range(olas):
        print(f"\n=== Ola {ola + 1} de {olas} ===", flush=True)
        if reset_inventario:
            resetear_inventario()
        tareas = []
        for escenario in ESCENARIOS:
            tareas.append(correr_caso(numero + 1, escenario, ZONAS[numero % len(ZONAS)], usuarios, bonita))
            numero += 1
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        for resultado in resultados:
            if isinstance(resultado, Exception):
                print(f"  ✗ {resultado!r}", flush=True)
        # Dar tiempo a que el proceso libere los recursos reservados antes de la ola siguiente.
        await asyncio.sleep(15)
    print("\nListo. Abrí el dashboard con un usuario directivo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--olas", type=int, default=2, help="Cantidad de olas de 4 casos (default 2 = 8 casos)")
    parser.add_argument("--reset-inventario", action="store_true",
                        help="Restablece el stock de la API Nacional antes de cada ola (necesario si la tarea de liberar recursos no devuelve el inventario)")
    args = parser.parse_args()
    asyncio.run(main(args.olas, args.reset_inventario))
