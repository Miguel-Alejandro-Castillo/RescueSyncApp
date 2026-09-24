from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


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
        default="creada",
        description="Estado de la emergencia"
    )

    fechaCreacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de creación de la emergencia"
    )