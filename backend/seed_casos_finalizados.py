"""Genera casos REALES de punta a punta (Bonita + base local) para alimentar el dashboard.

Recorre el proceso usando la API de RescueSync (igual que cada rol desde la pantalla) y
Bonita se entera de cada paso. Las instancias quedan finalizadas en el motor y los
registros locales son consistentes con ellas.

Reglas que respeta:
  * Una ONG participa UNA sola vez por emergencia (se identifica por CUIT), asi que cada
    participante de un consorcio es una ONG distinta (un usuario por ONG).
  * Cada recurso solo se ofrece a ONGs que lo tienen en la API Nacional.
  * Sin reset de inventario: cada ola usa recursos distintos y aportes de la mitad del
    stock disponible o menos. Con 12 casos o menos no se reutiliza ningun recurso.

Uso (stack levantado y seed de la API Nacional cargado), desde tu PC:
    python seed_casos_finalizados.py                  (2 olas de 6 casos = 12 casos)
    python seed_casos_finalizados.py --olas 1 --por-ola 4
Requiere: pip install httpx
"""
import argparse
import asyncio
import base64
import json
import os
import random
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = os.getenv("RESCUESYNC_API_URL", "http://localhost:3000/api/rescue")
BONITA = os.getenv("BONITA_ENGINE_URL", "http://localhost:8080/bonita")
PASSWORD = "bpm"
MUNICIPAL, COORDINADOR = "william.jobs", "michael.morrison"
BONITA_USER = ("bonita.bpm", "bpm")

# Un usuario por ONG (distinto CUIT cada una).
ONGS = {
    "CRA": "jesse.pinkman",          # Cruz Roja
    "CARITAS": "lalo.salamanca",
    "SI": "kim.wexler",              # Fundacion Si
    "HUESPED": "don.eladio",
    "CRUZADA": "skylar.white",
    "POTENCIAR": "leonel.salamanca",
    "CULTURA": "hector.salamanca",
    "BANCO": "thomas.wallis",        # Banco de Alimentos
}

# (tipo, recurso, stock disponible por ONG tras el seed, ONGs que lo tienen)
# Stock disponible: Insumos 50, Personal 80, Materiales 110, Transporte 140.
# Agua la tienen todas las ONGs (el seed la agrega a todas).
# El orden mezcla categorias: cada ola de 6 toma una muestra variada.
RECURSOS = [
    ("Insumos", "Agua", 50, ["CRA", "CARITAS", "SI", "HUESPED", "CRUZADA", "POTENCIAR", "CULTURA", "BANCO"]),
    ("Personal", "Bomberos", 80, ["CARITAS", "CRUZADA", "BANCO"]),
    ("Materiales", "Ladrillos", 110, ["HUESPED", "BANCO"]),
    ("Transporte", "Vehículos", 140, ["CARITAS", "HUESPED", "POTENCIAR", "BANCO"]),
    ("Insumos", "Raciones de comida", 50, ["CRA", "HUESPED", "CULTURA"]),
    ("Personal", "Medicos", 80, ["CRA", "HUESPED", "CULTURA"]),
    ("Transporte", "Combustible", 140, ["CRA", "SI", "CRUZADA", "CULTURA"]),
    ("Materiales", "Arena", 110, ["SI", "CULTURA"]),
    ("Insumos", "Medicamentos", 50, ["SI", "POTENCIAR"]),
    ("Personal", "Policias", 80, ["SI", "POTENCIAR"]),
    ("Materiales", "Tierra", 110, ["CRA", "CRUZADA"]),
    ("Materiales", "Cemento", 110, ["CARITAS", "POTENCIAR"]),
]
GRAVEDADES = ["critico", "alto", "medio", "bajo"]
ZONAS = ["Costa Norte", "Valle Central", "Sierra Sur", "Delta", "Puerto Viejo", "Barrio Los Pinos",
         "Ribera Oeste", "Alto Verde", "Lomas del Sur", "Isla Grande", "Paso del Rio", "Cerro Alto"]


def planificar(total, semilla=7):
    """Arma los casos: recurso, ONGs participantes (1 a 3, todas distintas) y sus aportes."""
    azar = random.Random(semilla)
    casos = []
    for i in range(total):
        tipo, recurso, disponible, tienen = RECURSOS[i % len(RECURSOS)]
        cuantas = min(len(tienen), azar.choice((1, 2, 3)))
        ongs = azar.sample(tienen, cuantas)
        aportes = [azar.randint(disponible // 4, disponible // 2) for _ in ongs]
        casos.append(dict(gravedad=GRAVEDADES[i % 4], zona=ZONAS[i % len(ZONAS)], tipo=tipo,
                          recurso=recurso, ongs=ongs, aportes=aportes, cantidad=sum(aportes)))
    return casos


def log(caso, mensaje):
    print(f"[{time.strftime('%H:%M:%S')}] caso {caso}: {mensaje}", flush=True)


def describir(error):
    """Texto legible de un error; en errores HTTP incluye lo que respondio el backend."""
    if isinstance(error, httpx.HTTPStatusError):
        r = error.response
        return f"{error.request.method} {error.request.url.path} -> {r.status_code}: {r.text[:300]}"
    return repr(error)


async def esperar(descripcion, intento, timeout=600, intervalo=5):
    """Repite `intento` hasta que devuelva algo verdadero o se acabe el tiempo."""
    limite = time.monotonic() + timeout
    ultimo = None
    while time.monotonic() < limite:
        try:
            resultado = await intento()
            if resultado:
                return resultado
        except httpx.HTTPStatusError as error:
            ultimo = describir(error)
        except httpx.TransportError as error:
            ultimo = repr(error)
        await asyncio.sleep(intervalo)
    raise TimeoutError(f"Se agoto el tiempo esperando: {descripcion}. Ultimo error: {ultimo}")


class Cliente:
    """Sesion autenticada de un usuario contra la API de RescueSync."""

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
    """Solo para verificar el cierre del caso (y destrabar 'Ejecutar y finalizar' si hiciera falta)."""

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


async def correr_caso(n, caso, clientes, bonita):
    municipal, coordinador = clientes[MUNICIPAL], clientes[COORDINADOR]
    usuarios_ong = [clientes[ONGS[o]] for o in caso["ongs"]]
    lider, invitados = usuarios_ong[0], usuarios_ong[1:]
    descripcion_ongs = ", ".join(f"{o} x{a}" for o, a in zip(caso["ongs"], caso["aportes"]))

    emergencia = await municipal.request("POST", "/emergencias", json={
        "zonaAfectada": caso["zona"], "nivelGravedad": caso["gravedad"], "usuarioCreador": "seed",
        "descripcionInicial": f"Caso de demostracion {n} para el dashboard"})
    emergencia_id, caso_bonita = emergencia["id"], emergencia["bonitaCaseId"]
    log(n, f"emergencia {emergencia_id} creada (caso Bonita {caso_bonita}, gravedad {caso['gravedad']})")

    lotes = await coordinador.request("POST", "/lotes", json={"emergenciaId": emergencia_id, "lotes": [
        {"tipoRecurso": caso["tipo"], "descripcion": caso["recurso"], "cantidad": caso["cantidad"]}]})
    lote_id = lotes[0]["id"]
    log(n, f"lote {lote_id} publicado ({caso['recurso']} x{caso['cantidad']}); la ventana ya corre")

    oferta = await lider.request("POST", "/ofertas/", json={
        "id_lote": lote_id, "cantidad_lider": caso["aportes"][0],
        "invitados": [int(c.user_id) for c in invitados]})
    oferta_id = oferta["oferta_id"]
    for cliente, aporte in zip(invitados, caso["aportes"][1:]):
        await cliente.request("POST", f"/ofertas/{oferta_id}/responder-invitacion",
                              json={"aceptar": True, "cantidad_aportada": aporte})
    log(n, f"oferta {oferta_id} cargada ({'consorcio' if invitados else 'individual'}: {descripcion_ongs})")

    async def validada():
        detalle = await coordinador.request("GET", f"/ofertas/{oferta_id}/detalle")
        return detalle if detalle["estado_validacion"] in ("valida", "invalida") else None

    detalle = await esperar("que venza la ventana y se valide la oferta", validada, timeout=1500)
    if detalle["estado_validacion"] != "valida":
        raise RuntimeError(f"La oferta {oferta_id} quedo invalida: {detalle.get('resultado_validacion')}")
    log(n, "oferta validada por la API Nacional")

    adjudicacion = [{"detalles": [
        {"participante_id": p["id"], "cantidad_adjudicada": p["cantidad_aportada"]}
        for p in detalle["participantes"] if p["cantidad_aportada"]]}]

    async def adjudicada():
        await municipal.request("POST", f"/ofertas/{lote_id}/adjudicaciones", json=adjudicacion)
        return True

    await esperar("que Bonita habilite la adjudicacion", adjudicada, timeout=300)
    log(n, "lote adjudicado")

    for cliente in usuarios_ong:
        await cliente.request("POST", f"/monitoreo/emergencias/{emergencia_id}/tareas-finalizadas")
    log(n, "las ONGs marcaron sus tareas como finalizadas")

    async def finalizado():
        await coordinador.request("POST", f"/monitoreo/emergencias/{emergencia_id}/finalizar")
        return True

    await esperar("finalizar el monitoreo", finalizado, timeout=180, intervalo=3)
    log(n, "monitoreo finalizado")

    async def caso_cerrado():
        # Si el backend ya completa 'Ejecutar y finalizar', esto no encuentra nada y no hace falta.
        for tarea in await bonita.tareas_listas(caso_bonita):
            if " ".join(tarea["name"].split()) == "Ejecutar y finalizar actividades de ayuda":
                await bonita.completar(tarea["id"])
        return await bonita.caso_finalizado(caso_bonita)

    await esperar("que Bonita archive el caso como finalizado", caso_cerrado, timeout=180, intervalo=3)
    log(n, "FINALIZADO en Bonita y en la base local")


async def main(olas, por_ola):
    casos = planificar(olas * por_ola)
    usuarios = {MUNICIPAL, COORDINADOR} | {ONGS[o] for c in casos for o in c["ongs"]}
    logueados = await asyncio.gather(*(Cliente(u).login() for u in sorted(usuarios)))
    clientes = {c.usuario: c for c in logueados}
    bonita = await BonitaAdmin().login()

    fallidos = 0
    for ola in range(olas):
        print(f"\n=== Ola {ola + 1} de {olas} ===", flush=True)
        tanda = [(ola * por_ola + i + 1, caso) for i, caso in enumerate(casos[ola * por_ola:(ola + 1) * por_ola])]
        resultados = await asyncio.gather(
            *(correr_caso(n, caso, clientes, bonita) for n, caso in tanda), return_exceptions=True)
        for (n, _), resultado in zip(tanda, resultados):
            if isinstance(resultado, Exception):
                fallidos += 1
                print(f"  X caso {n}: {describir(resultado)}", flush=True)
        if ola < olas - 1:
            await asyncio.sleep(15)  # margen para que el proceso libere recursos reservados

    print(f"\nListo: {len(casos) - fallidos} de {len(casos)} casos finalizados. "
          "Abri el dashboard con un usuario directivo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--olas", type=int, default=2, help="Cantidad de olas (default 2)")
    parser.add_argument("--por-ola", type=int, default=6, help="Casos en paralelo por ola (default 6)")
    args = parser.parse_args()
    asyncio.run(main(args.olas, args.por_ola))