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
from app.core.db.mixins import CatalogMixin, Timestamps, UUIDv7PK, VersionMixin

DOCUMENT_TYPE_VALUES = ("consentimiento_informado", "tratamiento_datos", "otro")

SIGNER_VALUES = ("paciente", "paciente_o_representante")


class ConsentDocument(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Documento a firmar (catálogo). El contenido versionado vive en
    `ConsentDocumentVersion`."""

    __tablename__ = "consent_documents"
    __table_args__ = (
        CheckConstraint(
            f"document_type IN {DOCUMENT_TYPE_VALUES}",
            name="document_type",
        ),
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
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)


class ConsentDocumentVersion(VersionMixin, UUIDv7PK, Timestamps, Base):
    """Version de un documento a firmar.

    Unico `(consent_document_id, version_number)`; indice unico parcial para
    que exista a lo sumo un `draft` por documento.
    """

    __tablename__ = "consent_document_versions"
    __table_args__ = (
        VersionMixin.status_check(),
        CheckConstraint(
            f"signer IN {SIGNER_VALUES}",
            name="signer",
        ),
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
    signer: Mapped[str] = mapped_column(String(32), nullable=False)
    # Archivo (PDF) del consentimiento: artefacto legal; `content` es su texto
    # equivalente. Los 4 campos van todos o ninguno. `file_base64` es diferido
    # (cientos de KB): solo se carga al acceder o con `undefer`. El sha256 y el
    # tamano los calcula la API sobre los bytes decodificados.
    file_base64: Mapped[str | None] = mapped_column(Text, nullable=True, deferred=True)
    file_content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
