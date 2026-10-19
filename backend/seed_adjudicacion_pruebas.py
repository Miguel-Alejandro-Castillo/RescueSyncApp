"""Seed idempotente para pruebas de adjudicación: python -m seed_adjudicacion_pruebas --demo [--dry-run]."""
import argparse
import os
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, create_engine, select

from models import Emergencia, Lote, Oferta, ParticipanteOferta
from models.emergencia import EmergenciaEstado
from models.lote import LoteEstado
from seed_demo import validate_target

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


def split_amount(total, parts):
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def create_offer(session, lot_id, leader_id, participant_amounts):
    offer = Oferta(lote_id=lot_id, ong_lider_id=leader_id)
    session.add(offer)
    session.flush()

    for offset, amount in enumerate(participant_amounts):
        session.add(ParticipanteOferta(
            oferta_id=offer.id,
            ong_id=leader_id + offset,
            cantidad_aportada=amount,
        ))

    return offer


def seed(session, now=None):
    now = now or datetime.now(timezone.utc)
    marker = f"{SEED_MARKER} Emergencia para adjudicar ofertas"
    existing = session.exec(select(Emergencia).where(Emergencia.zonaAfectada == marker)).first()
    if existing:
        return {
            "emergencias": 0,
            "lotes": 0,
            "ofertas": 0,
            "participantes": 0,
            "omitidos": 1,
            "emergencia_id": existing.id,
        }

    emergency = Emergencia(
        zonaAfectada=marker,
        nivelGravedad="alto",
        descripcionInicial="Fixture idempotente para probar adjudicación con ofertas individuales y en consorcio.",
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
        base_offer_amount = max(scenario["cantidad"] // total_offers, 1)

        for offer_index in range(individual_offers):
            offered_amount = base_offer_amount + (offer_index * 4)
            create_offer(session, lot.id, next_ong_id, [offered_amount])
            next_ong_id += 1
            offers_created += 1
            participants_created += 1

        for offer_index in range(consortium_offers):
            participants_count = 2 if offer_index % 2 == 0 else 3
            offered_total = base_offer_amount + 6 + (offer_index * 5)
            participant_amounts = split_amount(offered_total, participants_count)
            create_offer(session, lot.id, next_ong_id, participant_amounts)
            next_ong_id += participants_count
            offers_created += 1
            participants_created += participants_count

    session.flush()
    return {
        "emergencias": 1,
        "lotes": len(LOT_SCENARIOS),
        "ofertas": offers_created,
        "participantes": participants_created,
        "omitidos": 0,
        "emergencia_id": emergency.id,
    }


def main():
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
        help="Simular la carga SQL con rollback",
    )
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        parser.error("Falta DATABASE_URL. Ejecutá este comando dentro del servicio backend.")

    try:
        validate_target(url)
    except ValueError as error:
        parser.error(str(error))

    engine = create_engine(url, echo=False)
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

    print("Simulación revertida." if args.dry_run else "Seed de adjudicación completado.")
    print(result)


if __name__ == "__main__":
    main()
