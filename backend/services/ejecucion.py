"""ONGs adjudicadas en una emergencia y su avance en la ejecución."""
from sqlmodel import Session, select
from models.adjudicacion import Adjudicacion
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.lote import Lote
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from models.trabajo_finalizado import TrabajoFinalizado


def ongs_adjudicadas(session: Session, emergencia_id: int) -> list[dict]:
    """Una entrada por ONG (CUIT) con lo que el municipal le adjudicó y si ya terminó su trabajo."""
    filas = session.exec(
        select(AdjudicacionDetalle, ParticipanteOferta, Oferta, Lote)
        .join(Adjudicacion, AdjudicacionDetalle.adjudicacion_id == Adjudicacion.id)
        .join(ParticipanteOferta, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
        .join(Oferta, ParticipanteOferta.oferta_id == Oferta.id)
        .join(Lote, Adjudicacion.lote_id == Lote.id)
        .where(Lote.emergenciaId == emergencia_id)
        .order_by(Lote.id)
    ).all()
    finalizados = {t.ong_cuit: t for t in session.exec(
        select(TrabajoFinalizado).where(TrabajoFinalizado.emergencia_id == emergencia_id)
    ).all()}

    ongs = {}
    for detalle, participante, oferta, lote in filas:
        ong = ongs.setdefault(participante.ong_cuit, {
            "cuit": participante.ong_cuit,
            "nombre": None,
            "lotes": [],
            "finalizado_en": finalizados[participante.ong_cuit].fecha if participante.ong_cuit in finalizados else None,
        })
        # El nombre de la ONG viene del Sistema Nacional, guardado en la validación de la oferta.
        ong["nombre"] = ong["nombre"] or next(
            (p.get("ong_nombre") for p in (oferta.resultado_validacion or {}).get("participantes", [])
             if p.get("participante_id") == participante.id), None)
        ong["lotes"].append({
            "lote_id": lote.id,
            "tipo": lote.tipoRecurso,
            "descripcion": lote.descripcion,
            "cantidad_adjudicada": detalle.cantidad_adjudicada,
        })

    for ong in ongs.values():
        ong["nombre"] = ong["nombre"] or f"ONG {ong['cuit']}"
    return list(ongs.values())
