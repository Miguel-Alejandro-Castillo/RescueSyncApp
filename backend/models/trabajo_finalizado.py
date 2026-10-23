from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class TrabajoFinalizado(SQLModel, table=True):
    """Una ONG adjudicada informa que terminó su trabajo en la emergencia."""
    __tablename__ = "trabajos_finalizados"
    __table_args__ = (UniqueConstraint("emergencia_id", "ong_cuit"),)

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID de la marca de trabajo finalizado"
    )

    emergencia_id: int = Field(
        foreign_key="emergencias.id",
        description="Emergencia en la que la ONG terminó su trabajo"
    )

    ong_cuit: str = Field(
        max_length=32,
        description="CUIT de la ONG; cualquiera de sus representantes puede marcarlo"
    )

    usuario_id: str = Field(
        max_length=255,
        description="ID del representante de la ONG que lo marcó"
    )

    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha en que se marcó el trabajo como finalizado"
    )
