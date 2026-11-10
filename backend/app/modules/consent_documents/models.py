"""Modelos del modulo `consent_documents`: documentos a firmar.

Tercera entidad versionada del proyecto, mismo patron de `VersionMixin` ya
validado en `print_labels` y `result_templates`.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import (
    CatalogMixin,
    CategoryMixin,
    Timestamps,
    UUIDv7PK,
    VersionMixin,
)


class ConsentDocumentType(CategoryMixin, UUIDv7PK, Timestamps, Base):
    """Tipo de documento a firmar (catálogo de categoría). `tratamiento_datos`
    es código de sistema: el índice único parcial de `consent_documents` y el
    endpoint abierto dependen de él."""

    __tablename__ = "consent_document_types"


class ConsentSigner(CategoryMixin, UUIDv7PK, Timestamps, Base):
    """Quién debe firmar un documento (catálogo de categoría)."""

    __tablename__ = "consent_signers"


class ConsentDocument(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Documento a firmar (catálogo). El contenido versionado vive en
    `ConsentDocumentVersion`."""

    __tablename__ = "consent_documents"
    __table_args__ = (
        # A lo sumo un consentimiento general de datos personales activo.
        Index(
            "uq_consent_documents_one_active_data_treatment",
            "document_type",
            unique=True,
            postgresql_where=text("document_type = 'tratamiento_datos' AND is_active"),
        ),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("consent_document_types.code"),
        nullable=False,
        index=True,
    )


class ConsentDocumentVersion(VersionMixin, UUIDv7PK, Timestamps, Base):
    """Version de un documento a firmar.

    Unico `(consent_document_id, version_number)`; indice unico parcial para
    que exista a lo sumo un `draft` por documento.
    """

    __tablename__ = "consent_document_versions"
    __table_args__ = (
        VersionMixin.status_check(),
        CheckConstraint(
            "file_content_type IN ('application/pdf')",
            name="file_content_type",
        ),
        CheckConstraint("file_sha256 ~ '^[0-9a-f]{64}$'", name="file_sha256"),
        CheckConstraint("file_size_bytes > 0", name="file_size_bytes"),
        CheckConstraint(
            "(file_base64 IS NULL AND file_content_type IS NULL "
            "AND file_sha256 IS NULL AND file_size_bytes IS NULL) OR "
            "(file_base64 IS NOT NULL AND file_content_type IS NOT NULL "
            "AND file_sha256 IS NOT NULL AND file_size_bytes IS NOT NULL)",
            name="file_all_or_none",
        ),
        UniqueConstraint("consent_document_id", "version_number"),
        Index(
            "uq_consent_document_versions_consent_document_id_draft",
            "consent_document_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    consent_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consent_documents.id"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    signer: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("consent_signers.code"),
        nullable=False,
        index=True,
    )
    # Archivo (PDF) del consentimiento: artefacto legal; `content` es su texto
    # equivalente. Los 4 campos van todos o ninguno. `file_base64` es diferido
    # (cientos de KB): solo se carga al acceder o con `undefer`. El sha256 y el
    # tamano los calcula la API sobre los bytes decodificados.
    file_base64: Mapped[str | None] = mapped_column(Text, nullable=True, deferred=True)
    file_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
