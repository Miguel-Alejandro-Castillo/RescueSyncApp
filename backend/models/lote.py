from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel

class Lote(SQLModel, table=True):
    __tablename__ = "lotes"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="ID del lote"
    )

    # Clave foranea que conecta con la tabla emergencias
    emergenciaId: int = Field(
        foreign_key="emergencias.id",
        description="ID de la emergencia asociada"
    )

    tipoRecurso: str = Field(
        min_length=1,
        max_length=50,
        description="Tipo de recurso solicitado (Insumos, Personal, Maquinaria, Refugio)"
    )

    descripcion: str = Field(
        min_length=1,
        max_length=255,
        description="Descripción específica del recurso necesario"
    )

    cantidad: int = Field(
        gt=0,
        description="Cantidad requerida del recurso"
    )

    cantidadCubierta: int = Field(
        default=0,
        ge=0,
        description="Cantidad Cubierta por todas las ofertas"
    )

    estado: str = Field(
        min_length=1,
        max_length=50,
        default="creado",
        description="Estado del lote"
    )

    fechaLimiteConvocatoria: datetime = Field(
        description="Fecha y hora límite de la convocatoria para este lote"
    )

    fechaCreacion: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha de creación del lote"
    )