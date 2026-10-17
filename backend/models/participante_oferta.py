from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

class ParticipanteOferta(SQLModel, table=True):
    __tablename__ = "participantes_oferta"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID del participante de la oferta"
    )

    oferta_id: int = Field(
        foreign_key="ofertas.id",
        description="Oferta a la que pertenece la participación"
    )

    ong_id: int = Field(
        description="ONG participante"
    )

    ong_cuit: str | None = Field(
        default=None, max_length=32,
        description="CUIT de la ONG al confirmar el aporte; no cambia con el representante"
    )

    cantidad_aportada: int | None = Field(
        default=None,
        gt=0,
        description="Cantidad comprometida por la ONG. NULL indica que fue invitada pero aún no confirmó."
    )
