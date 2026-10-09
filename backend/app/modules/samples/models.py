"""Modelos del modulo `samples`: muestras y sus tipos.

Dos tablas en relacion 1:N: una muestra (`samples`, catálogo) agrupa varios
tipos de tubo/recipiente de toma (`sample_types`), cada uno con su propio
`code` de catálogo y los datos de recoleccion (color de tapa, aditivo,
especimen, volumen, temperatura y estabilidad de almacenamiento, orden de
llenado).
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import CatalogMixin, Timestamps, UUIDv7PK

SPECIMEN_VALUES = (
    "suero",
    "plasma",
    "sangre_total",
    "orina",
    "heces",
    "secrecion",
    "otro",
)


class Sample(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Muestra (catálogo): agrupa los tipos de tubo que la recolectan."""

    __tablename__ = "samples"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SampleType(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Tipo de tubo/recipiente de toma de una muestra."""

    __tablename__ = "sample_types"
    __table_args__ = (
        CheckConstraint(
            f"specimen IN {SPECIMEN_VALUES}",
            name="specimen",
        ),
    )

    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("samples.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    cap_color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    additive: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specimen: Mapped[str] = mapped_column(String(16), nullable=False)
    volume_ml: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    storage_temperature: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stability_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draw_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collection_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
