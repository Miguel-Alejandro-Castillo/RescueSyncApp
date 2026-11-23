"""Un solo comando: limpia todo, carga todo y deja los datos "viejos".

Pasos:
  1. Limpia: casos de Bonita, tablas del backend y reservas de la API Nacional.
  2. (Opcional) Corre el seed de la API Nacional  -> --seed-nacional "npx prisma run seed"
  3. Casos finalizados para el dashboard           -> seed_casos_finalizados.py
  4. Casos detenidos en cada etapa                 -> seed_escenarios.py
  5. "Envejece" las fechas de la BD local: reparte los casos en el pasado y estira
     las duraciones, para que el dashboard no muestre todo de hoy y en minutos.
  6. Casos con convocatoria abierta (ultimo, para que su ventana no venza).

Colocar junto a seed_escenarios.py, en la raiz del repo (donde esta docker-compose.yml).

Uso:
    python cargar_todo.py
    python cargar_todo.py --olas 1 --abiertas saltear
    python cargar_todo.py --seed-nacional "npm run seed"      (tras 'docker compose down -v')

IMPORTANTE: para cargar rapido, bajar los minutos de ventana del backend a 1, 2, 3 y 4
(critico, alto, medio, bajo) y reconstruir el backend. El paso 6 necesita ventanas LARGAS:
por eso el script se detiene y te pide devolver los valores originales.
Requiere: pip install httpx
"""
import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
BONITA = "http://localhost:8080/bonita"

TABLAS_BACKEND = ("emergencias, lotes, ofertas, participantes_oferta, adjudicaciones, "
                  "detalles_adjudicacion, eventos_ejecucion")

SQL_RESET_NACIONAL = """
delete from "Compromiso";
delete from "ReservaConvocatoria";
update "OngRecurso" o
   set "cantidadReservada" = 50 + 20 * (case c.codigo when 'INS' then 0 when 'PER' then 1 when 'MAT' then 2 else 3 end)
  from "Recurso" r join "Categoria" c on c.id = r."categoriaId"
 where r.id = o."recursoId";
"""

# Mueve cada emergencia (id * DIAS dias) al pasado y multiplica sus duraciones por K.
# No toca las que estan en 'publicada' (convocatoria abierta, ventana viva).
SQL_ENVEJECER = """
BEGIN;
CREATE TEMP TABLE m AS
SELECT id, "fechaCreacion" AS base,
       ((id * @DIAS@)::text || ' days')::interval AS atras,
       @K@::float8 AS k
FROM emergencias WHERE estado <> 'publicada';

UPDATE lotes l SET
  "fechaCreacion" = m.base - m.atras + (l."fechaCreacion" - m.base) * m.k,
  "fechaLimiteConvocatoria" = m.base - m.atras + (l."fechaLimiteConvocatoria" - m.base) * m.k
FROM m WHERE l."emergenciaId" = m.id;

UPDATE ofertas o SET
  fecha_creacion = m.base - m.atras + (o.fecha_creacion - m.base) * m.k,
  validada_en = m.base - m.atras + (o.validada_en - m.base) * m.k,
  ventana_validada = m.base - m.atras + (o.ventana_validada - m.base) * m.k,
  descartada_en = m.base - m.atras + (o.descartada_en - m.base) * m.k
FROM lotes l JOIN m ON l."emergenciaId" = m.id
WHERE o.lote_id = l.id;

UPDATE adjudicaciones a SET
  fecha_adjudicacion = m.base - m.atras + (a.fecha_adjudicacion - m.base) * m.k
FROM lotes l JOIN m ON l."emergenciaId" = m.id
WHERE a.lote_id = l.id;

UPDATE eventos_ejecucion e SET
  fecha = m.base - m.atras + (e.fecha - m.base) * m.k
FROM lotes l JOIN m ON l."emergenciaId" = m.id
WHERE e.lote_id = l.id;

UPDATE emergencias e SET "fechaCreacion" = m.base - m.atras
FROM m WHERE e.id = m.id;
COMMIT;
"""


def paso(texto):
    print(f"\n{'=' * 60}\n[{time.strftime('%H:%M:%S')}] {texto}\n{'=' * 60}", flush=True)


def correr(cmd, **kw):
    r = subprocess.run(cmd, cwd=kw.pop("cwd", RAIZ), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print(r.stdout, r.stderr, sep="\n")
        raise SystemExit(f"Fallo el comando: {' '.join(map(str, cmd))}")
    return r.stdout


def psql_backend(sql):
    return correr(["docker", "compose", "exec", "-T", "bonita-db", "psql", "-U", "bonita",
                   "-d", "rescuesync", "-v", "ON_ERROR_STOP=1", "-c", sql])


def psql_nacional(sql):
    return correr(["docker", "exec", "api-nacional-db", "psql", "-U", "postgres",
                   "-d", "api_nacional", "-v", "ON_ERROR_STOP=1", "-c", sql])


def limpiar_bonita():
    c = httpx.Client(base_url=BONITA, timeout=60)
    c.post("/loginservice", data={"username": "walter.bates", "password": "bpm",
                                  "redirect": "false"}).raise_for_status()
    c.headers["X-Bonita-API-Token"] = c.cookies.get("X-Bonita-API-Token")
    for ruta in ("case", "archivedCase"):
        borrados = fallidos = 0
        while True:
            items = c.get(f"/API/bpm/{ruta}", params={"p": 0, "c": 100}).json()
            if not items:
                break
            ok = sum(1 for it in items if c.delete(f"/API/bpm/{ruta}/{it['id']}").status_code < 300)
            borrados += ok
            fallidos += len(items) - ok
            if ok == 0:
                break
        print(f"  Bonita {ruta}: {borrados} borrados, {fallidos} no se pudieron borrar")
        if fallidos:
            print("  ! Los que no se borraron siguen en Bonita. Para limpiarlos del todo: "
                  "docker compose down -v (y redesplegar el proceso).")


def buscar(nombre):
    for p in RAIZ.rglob(nombre):
        if "node_modules" not in p.parts and "venv" not in str(p):
            return p
    raise SystemExit(f"No encontre {nombre} dentro de {RAIZ}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--olas", type=int, default=2, help="olas de 4 casos finalizados para el dashboard (0 = ninguna)")
    ap.add_argument("--seed-nacional", help='comando del seed, ej: "npm run seed" (solo tras borrar volumenes)')
    ap.add_argument("--abiertas", choices=["pausa", "saltear", "ahora"], default="pausa",
                    help="pausa: te pide restaurar los minutos largos; ahora: sin pausa; saltear: no carga")
    ap.add_argument("--dias-por-id", type=int, default=7, help="cuantos dias hacia atras por numero de emergencia")
    ap.add_argument("--factor-duracion", type=float, default=3.0, help="multiplica las duraciones de los casos")
    ap.add_argument("--sin-envejecer", action="store_true")
    args = ap.parse_args()
    inicio = time.time()

    paso("1/6 Limpiando Bonita, backend y API Nacional")
    limpiar_bonita()
    psql_backend(f"TRUNCATE {TABLAS_BACKEND} RESTART IDENTITY CASCADE;")
    print("  Tablas del backend vaciadas")
    psql_nacional(SQL_RESET_NACIONAL)
    print("  API Nacional: compromisos y reservas restablecidos")

    if args.seed_nacional:
        paso("2/6 Seed de la API Nacional")
        correr(["docker", "compose", "exec", "-T", "nacional", *args.seed_nacional.split()])
        print("  Seed cargado")
    else:
        print("\n(2/6 seed de la API Nacional omitido: solo hace falta tras 'down -v')")

    if args.olas > 0:
        paso(f"3/6 Casos finalizados para el dashboard ({args.olas} olas)")
        ruta = buscar("seed_casos_finalizados.py")
        r = subprocess.run([sys.executable, str(ruta), "--olas", str(args.olas), "--reset-inventario"],
                           cwd=ruta.parent)
        if r.returncode != 0:
            print("  ! seed_casos_finalizados.py termino con error; sigo con el resto")

    paso("4/6 Casos detenidos en cada etapa")
    import seed_escenarios as esc
    asyncio.run(esc.main("sin_abiertas", False))

    if not args.sin_envejecer:
        paso("5/6 Envejeciendo fechas de la BD local")
        sql = SQL_ENVEJECER.replace("@DIAS@", str(args.dias_por_id)).replace("@K@", str(args.factor_duracion))
        correr(["docker", "compose", "exec", "-T", "bonita-db", "psql", "-U", "bonita", "-d", "rescuesync",
                "-v", "ON_ERROR_STOP=1"], input=sql)
        print("  Fechas movidas al pasado y duraciones multiplicadas por", args.factor_duracion)
        print("  ! Pendiente: las fechas que vienen de Bonita siguen siendo de hoy (ver notas).")

    if args.abiertas == "saltear":
        print("\n(6/6 convocatorias abiertas omitidas; correlas despues con: python seed_escenarios.py --solo abiertas)")
    else:
        paso("6/6 Convocatorias abiertas")
        if args.abiertas == "pausa":
            input("Restaura los minutos ORIGINALES de ventana (4, 8, 12, 16) y reconstruí el backend "
                  "(docker compose up -d --build backend). Cuando termine, Enter para continuar... ")
        asyncio.run(esc.main("abiertas", False))

    print(f"\nListo en {(time.time() - inicio) / 60:.1f} minutos.")


if __name__ == "__main__":
    main()
