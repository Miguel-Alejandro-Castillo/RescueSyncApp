"""Cálculos puros del dashboard (sin base de datos ni red) para poder probarlos aislados."""
import csv
import io
from datetime import datetime, timezone

# Etapas humanas del proceso BPMN, en el orden del flujo.
ETAPAS_PROCESO = [
    "Registrar emergencia",
    "Generar lotes de necesidades",
    "Evaluar acciones a tomar",
    "Cargar ofertas de ayuda",
    "Adjudicar ofertas y notificar a ONGs",
    "Ejecutar y finalizar actividades de ayuda",
    "Monitorear la ejecucion",
]

FORMATOS_FECHA_BONITA = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")


def normalizar_nombre(nombre: str) -> str:
    return " ".join((nombre or "").split())


def parsear_fecha_bonita(valor) -> datetime | None:
    """Bonita devuelve fechas como 'YYYY-MM-DD HH:MM:SS.mmm' sin zona; se asumen UTC."""
    if not valor or not isinstance(valor, str):
        return None
    for formato in FORMATOS_FECHA_BONITA:
        try:
            return datetime.strptime(valor, formato).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def rango_mes(mes: str | None) -> tuple[datetime | None, datetime | None]:
    """'YYYY-MM' -> [primer día del mes, primer día del mes siguiente). None -> sin filtro."""
    if not mes:
        return None, None
    try:
        desde = datetime.strptime(mes, "%Y-%m").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("El mes debe tener formato AAAA-MM (por ejemplo 2026-11).")
    hasta = desde.replace(year=desde.year + 1, month=1) if desde.month == 12 else desde.replace(month=desde.month + 1)
    return desde, hasta


def en_rango(fecha: datetime | None, desde: datetime | None, hasta: datetime | None) -> bool:
    if fecha is None:
        return False
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return (desde is None or fecha >= desde) and (hasta is None or fecha < hasta)


def _horas(delta) -> float:
    return round(delta.total_seconds() / 3600, 2)


def calcular_tiempos_por_etapa(tareas: list[dict], casos_inicio: dict[str, datetime], desde=None, hasta=None) -> list[dict]:
    """Tiempo de cada etapa = fin de la tarea - fin de la tarea anterior del mismo caso
    (la primera se mide desde el inicio del caso). Incluye las esperas automáticas entre tareas.
    """
    por_caso: dict[str, list[tuple[datetime, str]]] = {}
    for tarea in tareas:
        caso = str(tarea.get("caseId") or tarea.get("rootCaseId") or "")
        fin = parsear_fecha_bonita(tarea.get("reached_state_date") or tarea.get("archivedDate"))
        if caso not in casos_inicio or fin is None:
            continue
        por_caso.setdefault(caso, []).append((fin, normalizar_nombre(tarea.get("name"))))

    muestras: dict[str, list[float]] = {}
    for caso, items in por_caso.items():
        anterior = casos_inicio[caso]
        for fin, nombre in sorted(items):
            if en_rango(fin, desde, hasta) and fin >= anterior:
                muestras.setdefault(nombre, []).append((fin - anterior).total_seconds() / 3600)
            anterior = max(anterior, fin)

    orden = {nombre: i for i, nombre in enumerate(ETAPAS_PROCESO)}
    etapas = [
        {
            "etapa": nombre,
            "promedio_horas": round(sum(valores) / len(valores), 2),
            "minimo_horas": round(min(valores), 2),
            "maximo_horas": round(max(valores), 2),
            "muestras": len(valores),
        }
        for nombre, valores in muestras.items()
    ]
    return sorted(etapas, key=lambda e: (orden.get(e["etapa"], len(orden)), e["etapa"]))


def calcular_resumen_casos(casos_abiertos: list[dict], casos_archivados: list[dict], desde=None, hasta=None) -> dict:
    duraciones = []
    finalizados = 0
    for caso in casos_archivados:
        inicio = parsear_fecha_bonita(caso.get("start"))
        fin = parsear_fecha_bonita(caso.get("end_date"))
        if caso.get("state") != "completed" or not inicio or not fin or not en_rango(fin, desde, hasta):
            continue
        finalizados += 1
        duraciones.append((fin - inicio).total_seconds() / 3600)
    return {
        "en_curso": len(casos_abiertos),
        "finalizados": finalizados,
        "duracion_promedio_horas": round(sum(duraciones) / len(duraciones), 2) if duraciones else None,
    }


def inicio_de_casos(casos_abiertos: list[dict], casos_archivados: list[dict]) -> dict[str, datetime]:
    inicios = {}
    for caso in casos_abiertos:
        inicio = parsear_fecha_bonita(caso.get("start"))
        if inicio:
            inicios[str(caso["id"])] = inicio
    for caso in casos_archivados:
        inicio = parsear_fecha_bonita(caso.get("start"))
        if inicio:
            inicios[str(caso.get("sourceObjectId") or caso["id"])] = inicio
    return inicios


def meses_anteriores(ahora: datetime, cantidad: int) -> list[str]:
    """['AAAA-MM', ...] de los últimos `cantidad` meses (el actual al final)."""
    meses = []
    anio, mes = ahora.year, ahora.month
    for _ in range(cantidad):
        meses.append(f"{anio:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return meses[::-1]


DATASETS = {
    "suministros_por_tipo": ("suministros_por_tipo", ["tipo", "cantidad"]),
    "suministros_por_mes": ("suministros_por_mes", ["mes", "cantidad"]),
    "proyectos": ("proyectos", [
        "id", "zona", "gravedad", "estado", "fecha_creacion", "lotes_total", "lotes_adjudicados",
        "cobertura_pct", "ongs_adjudicadas", "ongs_finalizadas",
    ]),
    "etapas": (None, ["etapa", "promedio_horas", "minimo_horas", "maximo_horas", "muestras"]),
}


def filas_dataset(reporte: dict, dataset: str) -> tuple[list[str], list[dict]]:
    if dataset == "resumen":
        filas = [{"indicador": clave, "valor": valor} for clave, valor in reporte["kpis"].items()]
        return ["indicador", "valor"], filas
    if dataset not in DATASETS:
        raise ValueError("Dataset desconocido.")
    clave, columnas = DATASETS[dataset]
    filas = reporte["bonita"].get("etapas", []) if dataset == "etapas" else reporte[clave]
    return columnas, filas


def a_csv(columnas: list[str], filas: list[dict]) -> str:
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
    escritor.writeheader()
    escritor.writerows(filas)
    return salida.getvalue()
