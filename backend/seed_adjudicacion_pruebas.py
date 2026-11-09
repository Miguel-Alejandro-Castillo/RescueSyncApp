"""Seed regenerable para pruebas de adjudicación.

Uso:
    python -m seed_adjudicacion_pruebas --demo
    python -m seed_adjudicacion_pruebas --demo --dry-run
"""

import argparse
import os
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, create_engine, select

from models import (
    Adjudicacion,
    AdjudicacionDetalle,
    Emergencia,
    EventoEjecucion,
    Lote,
    Oferta,
    ParticipanteOferta,
)
from models.emergencia import EmergenciaEstado
from models.lote import LoteEstado


SEED_MARKER = "[PRUEBA ADJUDICACION v1]"
EMERGENCY_CREATOR = "2"

LOT_SCENARIOS = (
    {
        "tipo_recurso": "Insumos",
        "descripcion": "Medicamentos y botiquines para atención inmediata",
        "cantidad": 80,
        "ofertas_totales": 2,
    },
    {
        "tipo_recurso": "Materiales",
        "descripcion": "Arena, placas y elementos de contención",
        "cantidad": 140,
        "ofertas_totales": 4,
    },
    {
        "tipo_recurso": "Personal",
        "descripcion": "Cuadrillas de asistencia y logística territorial",
        "cantidad": 210,
        "ofertas_totales": 6,
    },
)


def split_amount(total: int, parts: int) -> list[int]:
    """Divide una cantidad entre varias partes sin perder el resto."""

    base, remainder = divmod(total, parts)

    return [
        base + (1 if index < remainder else 0)
        for index in range(parts)
    ]


def create_offer(
    session: Session,
    lot_id: int,
    leader_id: int,
    participant_amounts: list[int],
) -> Oferta:
    """Crea una oferta junto con sus participantes."""

    offer = Oferta(
        lote_id=lot_id,
        ong_lider_id=leader_id,
    )

    session.add(offer)
    session.flush()

    for offset, amount in enumerate(participant_amounts):
        participant = ParticipanteOferta(
            oferta_id=offer.id,
            ong_id=leader_id + offset,
            cantidad_aportada=amount,
        )

        session.add(participant)

    return offer


def remove_existing_fixture(session: Session, marker: str) -> dict:
    """Elimina el fixture anterior y sus registros relacionados."""

    existing = session.exec(
        select(Emergencia).where(Emergencia.zonaAfectada == marker)
    ).first()

    if not existing or existing.id is None:
        return {
            "emergencias": 0,
            "lotes": 0,
            "ofertas": 0,
            "participantes": 0,
        }

    lots = session.exec(
        select(Lote).where(Lote.emergenciaId == existing.id)
    ).all()
    lot_ids = [lot.id for lot in lots if lot.id is not None]

    offers = []
    if lot_ids:
        offers = session.exec(
            select(Oferta).where(Oferta.lote_id.in_(lot_ids))
        ).all()

    offer_ids = [offer.id for offer in offers if offer.id is not None]
    participants = []
    if offer_ids:
        participants = session.exec(
            select(ParticipanteOferta).where(
                ParticipanteOferta.oferta_id.in_(offer_ids)
            )
        ).all()

    participant_ids = [
        participant.id
        for participant in participants
        if participant.id is not None
    ]

    adjudications = []
    events = []
    if lot_ids:
        adjudications = session.exec(
            select(Adjudicacion).where(Adjudicacion.lote_id.in_(lot_ids))
        ).all()
        events = session.exec(
            select(EventoEjecucion).where(EventoEjecucion.lote_id.in_(lot_ids))
        ).all()

    adjudication_ids = [
        adjudication.id
        for adjudication in adjudications
        if adjudication.id is not None
    ]
    details_by_id = {}

    if participant_ids:
        details = session.exec(
            select(AdjudicacionDetalle).where(
                AdjudicacionDetalle.participante_oferta_id.in_(
                    participant_ids
                )
            )
        ).all()
        details_by_id.update({
            detail.id: detail
            for detail in details
            if detail.id is not None
        })

    if adjudication_ids:
        details = session.exec(
            select(AdjudicacionDetalle).where(
                AdjudicacionDetalle.adjudicacion_id.in_(adjudication_ids)
            )
        ).all()
        details_by_id.update({
            detail.id: detail
            for detail in details
            if detail.id is not None
        })

    for detail in details_by_id.values():
        session.delete(detail)
    session.flush()

    for adjudication in adjudications:
        session.delete(adjudication)
    for event in events:
        session.delete(event)
    session.flush()

    for participant in participants:
        session.delete(participant)
    session.flush()

    for offer in offers:
        session.delete(offer)
    session.flush()

    for lot in lots:
        session.delete(lot)
    session.flush()

    session.delete(existing)
    session.flush()

    return {
        "emergencias": 1,
        "lotes": len(lots),
        "ofertas": len(offers),
        "participantes": len(participants),
    }


def seed(session: Session, now: datetime | None = None) -> dict:
    """Crea una emergencia con lotes y ofertas para probar adjudicaciones."""

    now = now or datetime.now(timezone.utc)

    marker = f"{SEED_MARKER} Emergencia para adjudicar ofertas"
    removed = remove_existing_fixture(session, marker)

    emergency = Emergencia(
        zonaAfectada=marker,
        nivelGravedad="alto",
        descripcionInicial=(
            "Fixture idempotente para probar adjudicación "
            "con ofertas individuales y en consorcio."
        ),
        estado=EmergenciaEstado.PUBLICADA,
        usuarioCreador=EMERGENCY_CREATOR,
        fechaCreacion=now,
        bonitaCaseId=None,
    )

    session.add(emergency)
    session.flush()

    next_ong_id = 910001
    offers_created = 0
    participants_created = 0

    for index, scenario in enumerate(LOT_SCENARIOS, start=1):
        lot = Lote(
            emergenciaId=emergency.id,
            tipoRecurso=scenario["tipo_recurso"],
            descripcion=f"[PRUEBA] {scenario['descripcion']}",
            cantidad=scenario["cantidad"],
            cantidadCubierta=0,
            estado=LoteEstado.EN_ADJUDICACION,
            fechaCreacion=now + timedelta(minutes=index),
            fechaLimiteConvocatoria=now + timedelta(days=5),
            loteOrigenId=None,
        )

        session.add(lot)
        session.flush()

        total_offers = scenario["ofertas_totales"]
        individual_offers = total_offers // 2
        consortium_offers = total_offers - individual_offers

        base_offer_amount = max(
            scenario["cantidad"] // total_offers,
            1,
        )

        # Ofertas individuales: un único participante.
        for offer_index in range(individual_offers):
            offered_amount = base_offer_amount + (offer_index * 4)

            create_offer(
                session=session,
                lot_id=lot.id,
                leader_id=next_ong_id,
                participant_amounts=[offered_amount],
            )

            next_ong_id += 1
            offers_created += 1
            participants_created += 1

        # Ofertas en consorcio: dos o tres participantes.
        for offer_index in range(consortium_offers):
            participants_count = 2 if offer_index % 2 == 0 else 3
            offered_total = base_offer_amount + 6 + (offer_index * 5)

            participant_amounts = split_amount(
                total=offered_total,
                parts=participants_count,
            )

            create_offer(
                session=session,
                lot_id=lot.id,
                leader_id=next_ong_id,
                participant_amounts=participant_amounts,
            )

            next_ong_id += participants_count
            offers_created += 1
            participants_created += participants_count

    session.flush()

    return {
        "emergencias": 1,
        "lotes": len(LOT_SCENARIOS),
        "ofertas": offers_created,
        "participantes": participants_created,
        "eliminados": removed,
        "emergencia_id": emergency.id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--demo",
        action="store_true",
        required=True,
        help="Confirmar la carga del fixture de adjudicación",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular la carga SQL realizando rollback al finalizar",
    )

    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        parser.error(
            "Falta DATABASE_URL. "
            "Ejecutá este comando dentro del servicio backend."
        )

    engine = create_engine(database_url, echo=False)

    with Session(engine) as session:
        try:
            result = seed(session)

            if args.dry_run:
                session.rollback()
            else:
                session.commit()

        except Exception:
            session.rollback()
            raise

    if args.dry_run:
        print("Simulación revertida. No se guardaron cambios.")
    else:
        print("Seed de adjudicación completado.")

    print(result)


if __name__ == "__main__":
    main()