from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class EventoEjecucion(SQLModel, table=True):
    __tablename__ = "eventos_ejecucion"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID del evento"
    )

    lote_id: int = Field(
        foreign_key="lotes.id",
        description="Lote adjudicado al que corresponde el evento"
    )

    usuario_id: str = Field(
        max_length=255,
        description="ID del Centro Coordinador que registró el evento"
    )

    descripcion: str = Field(
        min_length=1,
        max_length=500,
        description="Descripción del evento"
    )

    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha del evento"
    )
