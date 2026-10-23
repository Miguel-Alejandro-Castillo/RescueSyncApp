from datetime import datetime, timezone
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON, DateTime

class Oferta(SQLModel, table=True):
    __tablename__ = "ofertas"

    estado_validacion: str = Field(default="pendiente", max_length=20)
    validada_en: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    ventana_validada: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    resultado_validacion: dict | None = Field(default=None, sa_column=Column(JSON))

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID de la oferta"
    )

    lote_id: int = Field(
        foreign_key="lotes.id",
        description="Lote al que aplica la oferta"
    )

    ong_lider_id: int = Field(
        description="ONG responsable de crear y administrar la oferta"
    )

    fecha_creacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de creación de la oferta"
    )

    valida: bool = Field(
        default=True,
        description="Indica si la oferta es válida"
    )


