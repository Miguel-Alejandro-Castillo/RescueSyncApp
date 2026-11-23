"""Deja casos REALES (Bonita + base local) detenidos en cada etapa del proceso.

Usa la API de RescueSync igual que cada rol desde la pantalla, asi Bonita y la BD
quedan consistentes. Complementa a seed_casos_finalizados.py (que lleva casos hasta el final).

Escenarios (fases):
  lotes        6 emergencias esperando "Generar lotes" (4 criticas)
  adjudicacion 2 casos con cobertura total -> lote EN_ADJUDICACION (uno con consorcio)
  evaluar      4 casos con cobertura insuficiente -> esperando "Evaluar acciones a tomar"
  ejecucion    2 casos adjudicados con varias ONGs -> Monitorear / Ejecutar y finalizar
  abiertas     3 emergencias con convocatoria abierta, sin ofertas ("Cargar ofertas")

Uso (con el stack levantado y los seeds de la API Nacional cargados), desde tu PC:
    python seed_escenarios.py
    python seed_escenarios.py --solo evaluar
    python seed_escenarios.py --reset-inventario     (solo al principio, ver nota)

Notas:
  * Las ventanas corren en minutos segun gravedad (critico 4, alto 8, medio 12, bajo 16).
    Las fases con ofertas tardan hasta ~13 min porque esperan a que venza la ventana.
  * 'abiertas' se corre ULTIMO a proposito: su ventana empieza al publicar y, si vence,
    el caso pasa solo a validacion. Conviene correrla justo antes de la demo/prueba.
  * --reset-inventario borra las reservas de la API Nacional: usalo solo antes de
    empezar, nunca con casos en curso (les borraria sus reservas).
Requiere: pip install httpx
"""
import argparse
import asyncio
import base64
import json
import subprocess
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "http://localhost:3000/api/rescue"
PASSWORD = "bpm"
MUNICIPAL, COORDINADOR = "william.jobs", "michael.morrison"

# Stock disponible por ONG tras el reset (INS 50, PER 80, MAT 110, TRA 140).
# Cada par (ONG, recurso) se usa una sola vez en todo el script para no pisar reservas.
# Nombres de recurso EXACTOS como en el seed de la API Nacional (sin tildes en Medicos/Policias).

# fase "lotes": (gravedad, zona, descripcion)
EMERGENCIAS_SIN_LOTES = [
    ("critico", "Costa Norte", "Inundacion con familias evacuadas"),
    ("critico", "Valle Central", "Incendio forestal cerca de zona poblada"),
    ("critico", "Sierra Sur", "Derrumbe bloquea acceso a tres barrios"),
    ("critico", "Delta", "Crecida extraordinaria de rios"),
    ("alto", "Puerto Viejo", "Temporal con danos en viviendas"),
    ("medio", "Barrio Los Pinos", "Corte prolongado de agua potable"),
]

# fase "abiertas": (gravedad, zona, [(tipo, recurso, cantidad), ...]); sin ofertas
EMERGENCIAS_ABIERTAS = [
    ("medio", "Ribera Oeste", [("Insumos", "Agua", 120), ("Personal", "Medicos", 30)]),
    ("bajo", "Alto Verde", [("Materiales", "Ladrillos", 300)]),
    ("bajo", "Costa Sur", [("Transporte", "Vehículos", 40), ("Insumos", "Raciones de comida", 200)]),
]

# fases con ofertas. aporte_lider/invitados: usuarios de Bonita (uno por ONG) y su aporte.
CASOS = [
    # --- adjudicacion: cobertura total ---
    dict(fase="adjudicacion", gravedad="alto", zona="Lomas del Sur", tipo="Insumos", recurso="Raciones de comida",
         cantidad=40, lider=("jesse.pinkman", 40), invitados=[]),                       # Cruz Roja
    dict(fase="adjudicacion", gravedad="medio", zona="Barrio Norte", tipo="Personal", recurso="Policias",
         cantidad=120, lider=("leonel.salamanca", 70), invitados=[("kim.wexler", 50)]),  # Potenciar + Fund. Si
    # --- evaluar: cobertura insuficiente ---
    dict(fase="evaluar", gravedad="critico", zona="Isla Grande", tipo="Insumos", recurso="Agua",
         cantidad=100, lider=("lalo.salamanca", 40), invitados=[]),                      # Caritas
    dict(fase="evaluar", gravedad="critico", zona="Paso del Rio", tipo="Personal", recurso="Bomberos",
         cantidad=120, lider=("mario.schrader", 60), invitados=[]),                      # Cruzada
    dict(fase="evaluar", gravedad="alto", zona="Cerro Alto", tipo="Materiales", recurso="Arena",
         cantidad=150, lider=("hector.salamanca", 100), invitados=[]),                   # Cultura de Trabajo
    dict(fase="evaluar", gravedad="medio", zona="La Cañada", tipo="Insumos", recurso="Medicamentos",
         cantidad=80, lider=("saul.goodman", 30), invitados=[]),                         # Fund. Si
    # --- ejecucion: varias ONGs, cobertura total, adjudicado ---
    dict(fase="ejecucion", gravedad="alto", zona="Villa Esperanza", tipo="Transporte", recurso="Combustible",
         cantidad=300, lider=("hector.salamanca", 120),
         invitados=[("walter.white", 100), ("kim.wexler", 80)]),                         # Cultura + Cruz Roja + Fund. Si
    dict(fase="ejecucion", gravedad="medio", zona="Santa Rosa", tipo="Transporte", recurso="Vehículos",
         cantidad=250, lider=("tuco.salamanca", 100),
         invitados=[("don.eladio", 100), ("marco.salamanca", 50)]),                      # Caritas + Huesped + Potenciar
]

RESET_INVENTARIO_SQL = """
delete from "ReservaConvocatoria";
update "OngRecurso" o
   set "cantidadReservada" = 50 + 20 * (case c.codigo when 'INS' then 0 when 'PER' then 1 when 'MAT' then 2 else 3 end)
  from "Recurso" r join "Categoria" c on c.id = r."categoriaId"
 where r.id = o."recursoId";
"""


def resetear_inventario():
    subprocess.run(["docker", "exec", "api-nacional-db", "psql", "-U", "postgres", "-d", "api_nacional",
                    "-c", RESET_INVENTARIO_SQL], check=True, capture_output=True)
    print("Inventario de la API Nacional restablecido.", flush=True)


def log(etiqueta, mensaje):
    print(f"[{time.strftime('%H:%M:%S')}] {etiqueta}: {mensaje}", flush=True)


async def esperar(descripcion, intento, timeout=600, intervalo=5):
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
            ultimo = repr(error)
        await asyncio.sleep(intervalo)
    raise TimeoutError(f"Se agoto el tiempo esperando: {descripcion}. Ultimo error: {ultimo}")


class Cliente:
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


async def crear_emergencia(municipal, gravedad, zona, descripcion):
    e = await municipal.request("POST", "/emergencias", json={
        "zonaAfectada": zona, "nivelGravedad": gravedad, "usuarioCreador": "seed",
        "descripcionInicial": descripcion})
    return e["id"], e["bonitaCaseId"]


async def fase_lotes(municipal):
    """Emergencias que quedan esperando 'Generar lotes de necesidades'."""
    resultados = []
    for gravedad, zona, descripcion in EMERGENCIAS_SIN_LOTES:
        eid, caso = await crear_emergencia(municipal, gravedad, zona, descripcion)
        log("lotes", f"emergencia {eid} ({gravedad}, {zona}) caso Bonita {caso}")
        resultados.append(("lotes", eid))
    return resultados


async def fase_abiertas(municipal, coordinador):
    """Emergencias con lotes publicados y la ventana corriendo, sin ofertas."""
    resultados = []
    for gravedad, zona, lotes in EMERGENCIAS_ABIERTAS:
        eid, caso = await crear_emergencia(municipal, gravedad, zona, "Convocatoria abierta para cargar ofertas")
        await coordinador.request("POST", "/lotes", json={"emergenciaId": eid, "lotes": [
            {"tipoRecurso": t, "descripcion": r, "cantidad": c} for t, r, c in lotes]})
        log("abiertas", f"emergencia {eid} ({gravedad}) publicada con {len(lotes)} lote(s); ventana corriendo")
        resultados.append(("abiertas", eid))
    return resultados


async def estado_emergencia(cliente, emergencia_id):
    e = await cliente.request("GET", f"/emergencias/{emergencia_id}")
    return e["estado"]


async def correr_caso(n, spec, clientes, municipal, coordinador):
    fase = spec["fase"]
    etiqueta = f"{fase} #{n}"
    lider_user, aporte_lider = spec["lider"]
    lider = clientes[lider_user]

    eid, caso = await crear_emergencia(municipal, spec["gravedad"], spec["zona"],
                                       f"Caso de prueba de la fase {fase}")
    log(etiqueta, f"emergencia {eid} ({spec['gravedad']}) caso Bonita {caso}")

    lotes = await coordinador.request("POST", "/lotes", json={"emergenciaId": eid, "lotes": [
        {"tipoRecurso": spec["tipo"], "descripcion": spec["recurso"], "cantidad": spec["cantidad"]}]})
    lote_id = lotes[0]["id"]
    log(etiqueta, f"lote {lote_id} publicado ({spec['recurso']} x{spec['cantidad']}); ventana corriendo")

    oferta = await lider.request("POST", "/ofertas/", json={
        "id_lote": lote_id, "cantidad_lider": aporte_lider,
        "invitados": [int(clientes[u].user_id) for u, _ in spec["invitados"]]})
    oferta_id = oferta["oferta_id"]
    for usuario, aporte in spec["invitados"]:
        await clientes[usuario].request("POST", f"/ofertas/{oferta_id}/responder-invitacion",
                                        json={"aceptar": True, "cantidad_aportada": aporte})
    log(etiqueta, f"oferta {oferta_id} cargada ({1 + len(spec['invitados'])} ONG)")

    destino = {"adjudicacion": "en_adjudicacion", "evaluar": "convocatoria_cerrada", "ejecucion": "en_adjudicacion"}[fase]

    async def alcanzo_estado():
        return await estado_emergencia(coordinador, eid) == destino

    await esperar(f"que la emergencia {eid} llegue a '{destino}'", alcanzo_estado, timeout=1200)
    log(etiqueta, f"emergencia en estado '{destino}'")

    if fase == "ejecucion":
        detalle = await coordinador.request("GET", f"/ofertas/{oferta_id}/detalle")
        adjudicacion = [{"detalles": [
            {"participante_id": p["id"], "cantidad_adjudicada": p["cantidad_aportada"]}
            for p in detalle["participantes"] if p["cantidad_aportada"]]}]

        async def adjudicada():
            await municipal.request("POST", f"/ofertas/{lote_id}/adjudicaciones", json=adjudicacion)
            return True

        await esperar("que Bonita habilite la adjudicacion", adjudicada, timeout=300)
        log(etiqueta, "adjudicado: queda en 'Monitorear' y 'Ejecutar y finalizar'")

    return fase, eid


async def main(solo, reset_inventario):
    usuarios = {MUNICIPAL, COORDINADOR}
    for spec in CASOS:
        usuarios.add(spec["lider"][0])
        usuarios.update(u for u, _ in spec["invitados"])
    logueados = await asyncio.gather(*(Cliente(u).login() for u in sorted(usuarios)))
    clientes = {c.usuario: c for c in logueados}
    municipal, coordinador = clientes[MUNICIPAL], clientes[COORDINADOR]

    if reset_inventario:
        resetear_inventario()

    resumen = []

    def juntar(resultados):
        for r in resultados:
            if isinstance(r, Exception):
                print(f"  X {r!r}", flush=True)
            elif isinstance(r, list):
                resumen.extend(r)
            else:
                resumen.append(r)

    if solo in ("todo", "sin_abiertas", "lotes"):
        juntar([await fase_lotes(municipal)])

    fases_con_ofertas = [f for f in ("adjudicacion", "evaluar", "ejecucion") if solo in ("todo", "sin_abiertas", f)]
    if fases_con_ofertas:
        tareas = [correr_caso(i + 1, spec, clientes, municipal, coordinador)
                  for i, spec in enumerate(CASOS) if spec["fase"] in fases_con_ofertas]
        juntar(await asyncio.gather(*tareas, return_exceptions=True))

    if solo in ("todo", "abiertas"):
        juntar([await fase_abiertas(municipal, coordinador)])

    print("\nResumen (fase -> id de emergencia):")
    for fase, eid in resumen:
        print(f"  {fase:13s} {eid}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", default="todo",
                        choices=["todo", "sin_abiertas", "lotes", "adjudicacion", "evaluar", "ejecucion", "abiertas"])
    parser.add_argument("--reset-inventario", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.solo, args.reset_inventario))
