from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class Oferta(SQLModel, table=True):
    __tablename__ = "ofertas"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID de la oferta"
    )

    id_lote: int = Field(
        foreign_key="lotes.id",
        description="ID del lote asociado a la oferta"
    )

    id_ong: int = Field(
        description="ID de la ONG que realiza la oferta"
    )

    cant_recurso: int = Field(
        gt=0,
        description="Cantidad de recursos ofrecidos"
    )


