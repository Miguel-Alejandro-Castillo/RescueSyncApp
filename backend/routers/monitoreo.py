from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from dependencies.bonita import get_bonita_service
from dependencies.jwt_auth import get_current_user
from dependencies.rbac import require_roles, CENTRO_COORDINADOR, REPRESENTANTE_ONG
from models.adjudicacion_detalle import AdjudicacionDetalle
from models.emergencia import Emergencia, EmergenciaEstado
from models.evento_ejecucion import EventoEjecucion
from models.lote import Lote, LoteEstado
from models.oferta import Oferta
from models.participante_oferta import ParticipanteOferta
from services.bonita_service import BonitaService

router = APIRouter(
    prefix="/monitoreo",
    tags=["monitoreo"]
)

class EventoRequest(BaseModel):
    descripcion: str

def get_participantes_adjudicados(session: Session, emergencia_id: int):
    return session.exec(
        select(ParticipanteOferta)
        .join(AdjudicacionDetalle, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
        .join(Oferta, Oferta.id == ParticipanteOferta.oferta_id)
        .join(Lote, Lote.id == Oferta.lote_id)
        .where(Lote.emergenciaId == emergencia_id)
        .distinct()
    ).all()

def get_ongs_de_emergencia(session: Session, emergencia_id: int):
    ongs = {}
    for participante in get_participantes_adjudicados(session, emergencia_id):
        finalizada = participante.tareas_finalizadas
        ongs[participante.ong_id] = ongs.get(participante.ong_id, True) and finalizada
    return ongs

@router.get("", dependencies=[Depends(require_roles(CENTRO_COORDINADOR))])
def get_monitoreo(session: Session = Depends(get_session)):
    emergencias = session.exec(
        select(Emergencia).where(Emergencia.estado != EmergenciaEstado.MONITOREO_FINALIZADO)
    ).all()

    respuesta = []
    for emergencia in emergencias:
        lotes = session.exec(
            select(Lote).where(
                Lote.emergenciaId == emergencia.id,
                Lote.estado == LoteEstado.ADJUDICADO
            )
        ).all()
        if not lotes:
            continue

        lista_lotes = []
        for lote in lotes:
            eventos = session.exec(
                select(EventoEjecucion)
                .where(EventoEjecucion.lote_id == lote.id)
                .order_by(EventoEjecucion.fecha.desc())
            ).all()
            lista_lotes.append({
                "id": lote.id,
                "tipo": lote.tipoRecurso,
                "descripcion": lote.descripcion,
                "cantidad": lote.cantidad,
                "eventos": [
                    {"id": e.id, "descripcion": e.descripcion, "fecha": e.fecha.isoformat()}
                    for e in eventos
                ]
            })

        ongs = get_ongs_de_emergencia(session, emergencia.id)

        respuesta.append({
            "id": emergencia.id,
            "zona": emergencia.zonaAfectada,
            "lotes": lista_lotes,
            "ongs": [
                {"ong_id": ong_id, "nombre": "ONG " + str(ong_id), "finalizada": finalizada}
                for ong_id, finalizada in ongs.items()
            ],
            "todas_finalizadas": len(ongs) > 0 and all(ongs.values())
        })

    return respuesta

@router.post(
    "/lotes/{lote_id}/eventos",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
def registrar_evento(
    lote_id: int,
    data: EventoRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")

    if lote.estado != LoteEstado.ADJUDICADO:
        raise HTTPException(status_code=400, detail="El lote todavía no fue adjudicado.")

    descripcion = data.descripcion.strip()
    if not descripcion:
        raise HTTPException(status_code=422, detail="Ingrese la descripción del evento.")
    if len(descripcion) > 500:
        raise HTTPException(status_code=422, detail="La descripción no puede superar los 500 caracteres.")

    evento = EventoEjecucion(
        lote_id=lote_id,
        usuario_id=str(current_user["user_id"]),
        descripcion=descripcion
    )
    session.add(evento)
    session.commit()
    session.refresh(evento)

    return evento

@router.get("/mis-tareas", dependencies=[Depends(require_roles(REPRESENTANTE_ONG))])
def get_mis_tareas(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    ong_id = int(current_user["user_id"])
    participantes = session.exec(
        select(ParticipanteOferta)
        .join(AdjudicacionDetalle, AdjudicacionDetalle.participante_oferta_id == ParticipanteOferta.id)
        .where(ParticipanteOferta.ong_id == ong_id)
        .distinct()
    ).all()

    emergencias = {}
    for participante in participantes:
        oferta = session.get(Oferta, participante.oferta_id)
        lote = session.get(Lote, oferta.lote_id)
        emergencia = session.get(Emergencia, lote.emergenciaId)
        if emergencia.estado == EmergenciaEstado.MONITOREO_FINALIZADO:
            continue

        if emergencia.id not in emergencias:
            emergencias[emergencia.id] = {
                "id": emergencia.id,
                "zona": emergencia.zonaAfectada,
                "lotes": [],
                "finalizada": True
            }

        detalles = session.exec(
            select(AdjudicacionDetalle).where(AdjudicacionDetalle.participante_oferta_id == participante.id)
        ).all()
        emergencias[emergencia.id]["lotes"].append({
            "id": lote.id,
            "tipo": lote.tipoRecurso,
            "descripcion": lote.descripcion,
            "cantidad_adjudicada": sum(d.cantidad_adjudicada for d in detalles)
        })
        if not participante.tareas_finalizadas:
            emergencias[emergencia.id]["finalizada"] = False

    return list(emergencias.values())

@router.post(
    "/emergencias/{emergencia_id}/tareas-finalizadas",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(REPRESENTANTE_ONG))]
)
def finalizar_tareas(
    emergencia_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="La emergencia no existe.")

    ong_id = int(current_user["user_id"])
    participantes = [
        p for p in get_participantes_adjudicados(session, emergencia_id)
        if p.ong_id == ong_id
    ]
    if not participantes:
        raise HTTPException(status_code=403, detail="Tu ONG no fue adjudicada en esta emergencia.")

    for participante in participantes:
        participante.tareas_finalizadas = True
        session.add(participante)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post(
    "/emergencias/{emergencia_id}/finalizar",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(CENTRO_COORDINADOR))]
)
async def finalizar_monitoreo(
    emergencia_id: int,
    bonita: BonitaService = Depends(get_bonita_service),
    session: Session = Depends(get_session)
):
    emergencia = session.get(Emergencia, emergencia_id)
    if not emergencia:
        raise HTTPException(status_code=404, detail="La emergencia no existe.")

    participantes = get_participantes_adjudicados(session, emergencia_id)
    if not participantes:
        raise HTTPException(status_code=409, detail="La emergencia no tiene ONGs adjudicadas.")

    if not all(p.tareas_finalizadas for p in participantes):
        raise HTTPException(status_code=409, detail="Todavía hay ONGs que no finalizaron sus tareas.")

    try:
        for oferta_id in {p.oferta_id for p in participantes}:
            oferta = session.get(Oferta, oferta_id)
            oferta.estado_validacion = "finalizada"
            session.add(oferta)

        emergencia.estado = EmergenciaEstado.MONITOREO_FINALIZADO
        session.add(emergencia)

        if emergencia.bonitaCaseId:
            tareas = await bonita.obtener_tareas_humanas_por_caso(emergencia.bonitaCaseId)
            tarea = next((t for t in tareas if t["name"].strip() == "Monitorear la ejecucion"), None)
            if tarea:
                await bonita.completar_tarea_humana(tarea["id"])

        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
