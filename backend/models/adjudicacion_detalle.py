from sqlmodel import Field, SQLModel

class AdjudicacionDetalle(SQLModel, table=True):
    __tablename__ = "detalles_adjudicacion"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID del detalle de adjudicación"
    )

    adjudicacion_id: int = Field(
        foreign_key="adjudicaciones.id",
        description="Adjudicación a la que pertenece"
    )

    participante_oferta_id: int = Field(
        foreign_key="participantes_oferta.id",
        description="Participación de la oferta adjudicada"
    )

    cantidad_adjudicada: int = Field(
        gt=0,
        description="Cantidad aceptada por el Operador Municipal"
    )
    