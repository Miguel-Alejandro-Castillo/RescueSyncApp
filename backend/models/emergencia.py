from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel
class EmergenciaEstado(str, Enum):
    CREADA = "creada"
    PUBLICADA = "publicada"
    CONVOCATORIA_CERRADA = "convocatoria_cerrada"
    EN_ADJUDICACION = "en_adjudicacion"
    ADJUDICADA = "adjudicada"
    MONITOREO_FINALIZADO = "monitoreo_finalizado"
class Emergencia(SQLModel, table=True):
    __tablename__ = "emergencias"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID de la emergencia"
    )

    zonaAfectada: str = Field(
        min_length=1,
        max_length=255,
        description="Zona afectada por la emergencia"
    )

    nivelGravedad: str = Field(
        min_length=1,
        max_length=20,
        description="Nivel de gravedad de la emergencia"
    )

    descripcionInicial: str = Field(
        min_length=1,
        max_length=500,
        description="Descripción inicial de la emergencia"
    )

    estado: str = Field(
        min_length=1,
        max_length=50,
        default=EmergenciaEstado.CREADA,
        description="Estado de la emergencia"
    )

    usuarioCreador: str = Field(
        min_length=1,
        max_length=255,
        description="Usuario Operador Municipal que creó la emergencia"
    )   

    fechaCreacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de creación de la emergencia"
    )
    
    bonitaCaseId: str | None = Field(
        default=None,
        description="ID del caso en Bonita asociado a la emergencia"
    )

    decisionesCoordinador: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
        description="Historial de decisiones del Centro Coordinador cuando la convocatoria cerró sin cobertura suficiente"
    )
