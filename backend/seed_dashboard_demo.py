"""Seed idempotente con historial de emergencias adjudicadas para probar el dashboard directivo.

Uso (dentro del servicio backend):
    python -m seed_dashboard_demo            # carga los datos
    python -m seed_dashboard_demo --dry-run  # simula y revierte
No crea casos en Bonita: los tiempos por etapa salen de los casos reales del proceso.
"""
import argparse
import os
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, create_engine, select

from models import Adjudicacion, AdjudicacionDetalle, Emergencia, Lote, Oferta, ParticipanteOferta
from models.emergencia import EmergenciaEstado
from models.lote import LoteEstado

MARCADOR = "[DEMO DASHBOARD]"
OPERADOR = "2"

# (meses atrás, zona, gravedad, estado, [(tipo, descripcion, cantidad, [integrantes por oferta adjudicada])])
ESCENARIOS = [
    (5, "Costa Norte", "alto", EmergenciaEstado.MONITOREO_FINALIZADO, [
        ("Insumos", "Frazadas y abrigo", 120, [[120]]),
        ("Alimentos", "Viandas calientes", 300, [[100, 100], [100]]),
    ]),
    (4, "Valle Central", "medio", EmergenciaEstado.MONITOREO_FINALIZADO, [
        ("Personal", "Brigadas de rescate", 60, [[30, 30]]),
        ("Insumos", "Botiquines", 90, [[90]]),
    ]),
    (3, "Sierra Sur", "alto", EmergenciaEstado.MONITOREO_FINALIZADO, [
        ("Maquinaria", "Bombas de achique", 20, [[10, 10]]),
        ("Alimentos", "Agua potable", 500, [[250, 150, 100]]),
    ]),
    (2, "Delta", "alto", EmergenciaEstado.ADJUDICADA, [
        ("Refugio", "Carpas familiares", 80, [[40], [40]]),
        ("Personal", "Voluntarios de logística", 45, [[15, 15, 15]]),
    ]),
    (1, "Puerto Viejo", "bajo", EmergenciaEstado.ADJUDICADA, [
        ("Insumos", "Kits de higiene", 150, [[75, 75]]),
    ]),
    (0, "Barrio Los Pinos", "medio", EmergenciaEstado.ADJUDICADA, [
        ("Alimentos", "Módulos alimentarios", 200, [[200]]),
        ("Maquinaria", "Grupos electrógenos", 12, [[6, 6]]),
    ]),
]


def hace_meses(ahora: datetime, meses: int) -> datetime:
    mes_total = ahora.year * 12 + (ahora.month - 1) - meses
    return ahora.replace(year=mes_total // 12, month=mes_total % 12 + 1, day=10, hour=12, minute=0, second=0, microsecond=0)


def cargar(session: Session, ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now(timezone.utc)
    if session.exec(select(Emergencia).where(Emergencia.descripcionInicial.startswith(MARCADOR))).first():
        return {"omitido": "ya estaba cargado"}

    contador = {"emergencias": 0, "lotes": 0, "ofertas": 0}
    ong_id = 920001
    for meses, zona, gravedad, estado, lotes in ESCENARIOS:
        fecha = hace_meses(ahora, meses)
        finalizada = estado == EmergenciaEstado.MONITOREO_FINALIZADO
        emergencia = Emergencia(
            zonaAfectada=zona, nivelGravedad=gravedad, estado=estado, usuarioCreador=OPERADOR,
            descripcionInicial=f"{MARCADOR} Datos de demostración para el dashboard.",
            fechaCreacion=fecha,
        )
        session.add(emergencia)
        session.flush()
        contador["emergencias"] += 1

        for tipo, descripcion, cantidad, ofertas in lotes:
            lote = Lote(
                emergenciaId=emergencia.id, tipoRecurso=tipo, descripcion=f"{MARCADOR} {descripcion}",
                cantidad=cantidad, cantidadCubierta=cantidad, estado=LoteEstado.ADJUDICADO,
                fechaCreacion=fecha, fechaLimiteConvocatoria=fecha + timedelta(days=2),
            )
            session.add(lote)
            session.flush()
            contador["lotes"] += 1

            adjudicacion = Adjudicacion(lote_id=lote.id, usuario_id=OPERADOR, fecha_adjudicacion=min(fecha + timedelta(days=3), ahora))
            session.add(adjudicacion)
            session.flush()

            for aportes in ofertas:
                oferta = Oferta(
                    lote_id=lote.id, ong_lider_id=ong_id, fecha_creacion=min(fecha + timedelta(days=1), ahora),
                    estado_validacion="finalizada" if finalizada else "pendiente",
                )
                session.add(oferta)
                session.flush()
                contador["ofertas"] += 1
                for aporte in aportes:
                    participante = ParticipanteOferta(
                        oferta_id=oferta.id, ong_id=ong_id, cantidad_aportada=aporte, tareas_finalizadas=finalizada,
                    )
                    session.add(participante)
                    session.flush()
                    session.add(AdjudicacionDetalle(
                        adjudicacion_id=adjudicacion.id, participante_oferta_id=participante.id, cantidad_adjudicada=aporte,
                    ))
                    ong_id += 1
    return contador


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Simular la carga y revertirla")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        parser.error("Falta DATABASE_URL. Ejecutá este comando dentro del servicio backend.")

    with Session(create_engine(url, echo=False)) as session:
        try:
            resultado = cargar(session)
            session.rollback() if args.dry_run else session.commit()
        except Exception:
            session.rollback()
            raise
    print("Simulación revertida." if args.dry_run else "Seed del dashboard completado.")
    print(resultado)


if __name__ == "__main__":
    main()
