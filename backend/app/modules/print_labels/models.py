"""Modelos del modulo `print_labels`: etiquetas de impresion y sus versiones.

Primera entidad versionada del proyecto: `print_label_versions` instancia el
patron de `VersionMixin` (columnas comunes + `status_check()`) documentado en
el archivo del subagente `database-postgres`. Ciclo de vida completo
(`draft` -> `published` -> `retired`) en la nota de bóveda `Versionado`.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import CatalogMixin, Timestamps, UUIDv7PK, VersionMixin

OUTPUT_FORMAT_VALUES = ("zpl", "html")


class PrintLabel(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Etiqueta de impresion (catálogo). El contenido versionado vive en
    `PrintLabelVersion`."""

    __tablename__ = "print_labels"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrintLabelVersion(VersionMixin, UUIDv7PK, Timestamps, Base):
    """Version de una etiqueta de impresion.

    Unico `(print_label_id, version_number)`; indice unico parcial para que
    exista a lo sumo un `draft` por etiqueta.
    """

    __tablename__ = "print_label_versions"
    __table_args__ = (
        VersionMixin.status_check(),
        CheckConstraint(
            f"output_format IN {OUTPUT_FORMAT_VALUES}",
            name="output_format",
        ),
        UniqueConstraint("print_label_id", "version_number"),
        Index(
            "uq_print_label_versions_print_label_id_draft",
            "print_label_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    print_label_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("print_labels.id"),
        nullable=False,
        index=True,
    )
    width_mm: Mapped[float] = mapped_column(Numeric, nullable=False)
    height_mm: Mapped[float] = mapped_column(Numeric, nullable=False)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False)
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    barcode_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    copies: Mapped[int] = mapped_column(Integer, nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    placeholders: Mapped[dict] = mapped_column(JSONB, nullable=False)
