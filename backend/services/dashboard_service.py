"""Indicadores del dashboard directivo: datos propios (BD) + datos de la API de Bonita."""
import os
from datetime import datetime, timezone

from sqlmodel import Session, col, func, select

from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.emergencia import Emergencia, EmergenciaEstado
from models.lote import Lote, LoteEstado
from models.participante_oferta import ParticipanteOferta
from services.bonita_service import BonitaService
from services.dashboard_calculos import (
    calcular_resumen_casos,
    calcular_tiempos_por_etapa,
    inicio_de_casos,
    meses_anteriores,
    rango_mes,
)

MESES_SERIE = 6


def _filtrar_fecha(stmt, columna, desde, hasta):
    if desde is not None:
        stmt = stmt.where(columna >= desde)
    if hasta is not None:
        stmt = stmt.where(columna < hasta)
    return stmt


def suministros_por_tipo(session: Session, desde, hasta) -> list[dict]:
    stmt = (
        select(Lote.tipoRecurso, func.sum(AdjudicacionDetalle.cantidad_adjudicada))
        .select_from(AdjudicacionDetalle)
        .join(Adjudicacion, Adjudicacion.id == AdjudicacionDetalle.adjudicacion_id)
        .join(Lote, Lote.id == Adjudicacion.lote_id)
        .group_by(Lote.tipoRecurso)
        .order_by(Lote.tipoRecurso)
    )
    stmt = _filtrar_fecha(stmt, Adjudicacion.fecha_adjudicacion, desde, hasta)
    return [{"tipo": tipo, "cantidad": int(cantidad or 0)} for tipo, cantidad in session.exec(stmt).all()]


def suministros_por_mes(session: Session, ahora: datetime) -> list[dict]:
    meses = meses_anteriores(ahora, MESES_SERIE)
    desde, _ = rango_mes(meses[0])
    stmt = (
        select(Adjudicacion.fecha_adjudicacion, AdjudicacionDetalle.cantidad_adjudicada)
        .select_from(AdjudicacionDetalle)
        .join(Adjudicacion, Adjudicacion.id == AdjudicacionDetalle.adjudicacion_id)
        .where(Adjudicacion.fecha_adjudicacion >= desde)
    )
    totales = {mes: 0 for mes in meses}
    for fecha, cantidad in session.exec(stmt).all():
        clave = f"{fecha.year:04d}-{fecha.month:02d}"
        if clave in totales:
            totales[clave] += cantidad
    return [{"mes": mes, "cantidad": cantidad} for mes, cantidad in totales.items()]


def resolucion_por_consorcios(session: Session, desde, hasta) -> dict:
    """Una oferta es 'consorcio' si tiene 2 o más ONGs que confirmaron aporte."""
    stmt = (
        select(ParticipanteOferta.oferta_id, func.sum(AdjudicacionDetalle.cantidad_adjudicada))
        .select_from(AdjudicacionDetalle)
        .join(Adjudicacion, Adjudicacion.id == AdjudicacionDetalle.adjudicacion_id)
        .join(ParticipanteOferta, ParticipanteOferta.id == AdjudicacionDetalle.participante_oferta_id)
        .group_by(ParticipanteOferta.oferta_id)
    )
    unidades_por_oferta = {
        oferta_id: int(cantidad or 0)
        for oferta_id, cantidad in session.exec(_filtrar_fecha(stmt, Adjudicacion.fecha_adjudicacion, desde, hasta)).all()
    }

    integrantes = {}
    if unidades_por_oferta:
        conteo = (
            select(ParticipanteOferta.oferta_id, func.count())
            .where(col(ParticipanteOferta.oferta_id).in_(list(unidades_por_oferta)))
            .where(col(ParticipanteOferta.cantidad_aportada).is_not(None))
            .group_by(ParticipanteOferta.oferta_id)
        )
        integrantes = dict(session.exec(conteo).all())

    consorcio = [oferta for oferta in unidades_por_oferta if integrantes.get(oferta, 1) >= 2]
    individuales = [oferta for oferta in unidades_por_oferta if oferta not in consorcio]
    total = len(unidades_por_oferta)
    return {
        "ofertas_total": total,
        "ofertas_consorcio": len(consorcio),
        "ofertas_individuales": len(individuales),
        "porcentaje_consorcio": round(100 * len(consorcio) / total, 1) if total else 0.0,
        "unidades_consorcio": sum(unidades_por_oferta[o] for o in consorcio),
        "unidades_individuales": sum(unidades_por_oferta[o] for o in individuales),
    }


def estado_de_proyectos(session: Session, desde, hasta) -> list[dict]:
    stmt = _filtrar_fecha(select(Emergencia).order_by(Emergencia.id), Emergencia.fechaCreacion, desde, hasta)
    proyectos = []
    for emergencia in session.exec(stmt).all():
        lotes = session.exec(select(Lote).where(Lote.emergenciaId == emergencia.id)).all()
        requerido = sum(lote.cantidad for lote in lotes)
        cubierto = sum(min(lote.cantidadCubierta, lote.cantidad) for lote in lotes)

        participantes = session.exec(
            select(ParticipanteOferta)
            .join(AdjudicacionDetalle, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
            .join(Adjudicacion, Adjudicacion.id == AdjudicacionDetalle.adjudicacion_id)
            .join(Lote, Lote.id == Adjudicacion.lote_id)
            .where(Lote.emergenciaId == emergencia.id)
            .distinct()
        ).all()
        ongs = {}
        for participante in participantes:
            ongs[participante.ong_id] = ongs.get(participante.ong_id, True) and participante.tareas_finalizadas

        proyectos.append({
            "id": emergencia.id,
            "zona": emergencia.zonaAfectada,
            "gravedad": emergencia.nivelGravedad,
            "estado": emergencia.estado,
            "fecha_creacion": emergencia.fechaCreacion.isoformat(),
            "lotes_total": len(lotes),
            "lotes_adjudicados": sum(1 for lote in lotes if lote.estado == LoteEstado.ADJUDICADO),
            "cobertura_pct": round(100 * cubierto / requerido, 1) if requerido else 0.0,
            "ongs_adjudicadas": len(ongs),
            "ongs_finalizadas": sum(1 for finalizada in ongs.values() if finalizada),
        })
    return proyectos


def proyectos_por_estado(proyectos: list[dict]) -> list[dict]:
    conteo = {estado.value: 0 for estado in EmergenciaEstado}
    for proyecto in proyectos:
        conteo[proyecto["estado"]] = conteo.get(proyecto["estado"], 0) + 1
    return [{"estado": estado, "cantidad": cantidad} for estado, cantidad in conteo.items()]


async def datos_bonita(bonita: BonitaService, desde, hasta) -> dict:
    """Si Bonita no responde, el dashboard sigue mostrando los datos propios."""
    try:
        procesos = await bonita.obtener_procesos_por_nombre(os.getenv("BONITA_PROCESS"))
        abiertos, archivados = [], []
        for proceso in procesos:
            abiertos += await bonita.obtener_casos_por_proceso(proceso["id"])
            archivados += await bonita.obtener_casos_archivados_por_proceso(proceso["id"])
        inicios = inicio_de_casos(abiertos, archivados)
        tareas = await bonita.obtener_tareas_humanas_archivadas()
        return {
            "disponible": True,
            "error": None,
            "casos": calcular_resumen_casos(abiertos, archivados, desde, hasta),
            "etapas": calcular_tiempos_por_etapa(tareas, inicios, desde, hasta),
        }
    except Exception as error:
        return {"disponible": False, "error": f"No se pudo consultar Bonita: {error}", "casos": None, "etapas": []}


async def generar_reporte(session: Session, bonita: BonitaService, mes: str | None) -> dict:
    desde, hasta = rango_mes(mes)
    ahora = datetime.now(timezone.utc)

    por_tipo = suministros_por_tipo(session, desde, hasta)
    consorcios = resolucion_por_consorcios(session, desde, hasta)
    proyectos = estado_de_proyectos(session, desde, hasta)
    finalizados = sum(1 for p in proyectos if p["estado"] == EmergenciaEstado.MONITOREO_FINALIZADO)
    bonita_datos = await datos_bonita(bonita, desde, hasta)

    return {
        "periodo": {
            "mes": mes,
            "desde": desde.isoformat() if desde else None,
            "hasta": hasta.isoformat() if hasta else None,
        },
        "generado_en": ahora.isoformat(),
        "kpis": {
            "suministros_movilizados": sum(item["cantidad"] for item in por_tipo),
            "porcentaje_resolucion_consorcios": consorcios["porcentaje_consorcio"],
            "emergencias_total": len(proyectos),
            "emergencias_finalizadas": finalizados,
            "porcentaje_finalizadas": round(100 * finalizados / len(proyectos), 1) if proyectos else 0.0,
            "casos_en_curso_bonita": bonita_datos["casos"]["en_curso"] if bonita_datos["casos"] else None,
            "duracion_promedio_caso_horas": bonita_datos["casos"]["duracion_promedio_horas"] if bonita_datos["casos"] else None,
        },
        "suministros_por_tipo": por_tipo,
        "suministros_por_mes": suministros_por_mes(session, ahora),
        "consorcios": consorcios,
        "proyectos_por_estado": proyectos_por_estado(proyectos),
        "proyectos": proyectos,
        "bonita": bonita_datos,
    }
