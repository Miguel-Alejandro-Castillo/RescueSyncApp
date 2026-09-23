from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Emergencia(SQLModel, table=True):
    __tablename__ = "emergencias"

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    zonaAfectada: str = Field(
        min_length=1,
        max_length=255,
    )

    nivelGravedad: str = Field(
        min_length=1,
        max_length=20,
    )

    descripcionInicial: str = Field(
        min_length=1,
    )

    fechaCreacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )