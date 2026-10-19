from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class Adjudicacion(SQLModel, table=True):
    __tablename__ = "adjudicaciones"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID de la adjudicación"
    )

    lote_id: int = Field(
        foreign_key="lotes.id",
        description="Lote al que corresponde la adjudicación"
    )

    usuario_id: str = Field(
        max_length=255,
        description="ID del usuario Operador Municipal que realizó la adjudicación"
    )

    fecha_adjudicacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de la adjudicación"
    )