from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class Oferta(SQLModel, table=True):
    __tablename__ = "ofertas"

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


