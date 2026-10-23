"""Esquemas Pydantic de entrada/salida del modulo `consent_documents`.

Dos recursos: `ConsentDocument` (catalogo) y `ConsentDocumentVersion`
(contenido versionado, ciclo `draft` -> `published` -> `retired`, ver
`app.core.versioning`). `ConsentDocumentVersionRead` siempre incluye
`status`; las reglas de que solo un `draft` es editable las aplica el
controller, no el schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.core.schemas import ActivityReasonInput, CodeStr
from app.core.versioning import VersionOwnerRead, VersionStatus
from app.modules.consent_documents.models import DOCUMENT_TYPE_VALUES, SIGNER_VALUES

# Enums derivados de los CHECK de `models.py` (fuente unica de los valores).
DocumentType = Literal[DOCUMENT_TYPE_VALUES]
Signer = Literal[SIGNER_VALUES]

# Consentimiento general (se firma primero, aplica a todo paciente, no se
# enlaza a examenes): a lo sumo uno activo.
DATA_TREATMENT_TYPE = "tratamiento_datos"

FILE_BASE64_DESCRIPTION = (
    "PDF en base64 estricto (sin prefijo `data:` ni saltos de línea); máximo "
    "`files.consent_max_mib` MiB (ajuste; 5 por defecto) ya decodificado y debe empezar por `%PDF-`. La API calcula "
    "`file_sha256`, `file_size_bytes` y `file_content_type`."
)


class ConsentDocumentBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    description: str | None = None
    document_type: DocumentType


class ConsentDocumentCreate(ConsentDocumentBase):
    is_active: bool = True


class ConsentDocumentUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    document_type: DocumentType | None = None
    is_active: bool | None = None


class ConsentDocumentRead(ConsentDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConsentDocumentVersionCreate(BaseModel):
    """Body de `POST /consent-documents/{id}/versions`.

    Si el documento ya tiene una version previa (publicada o retirada), el
    nuevo draft la clona y estos campos son overrides opcionales. Si es la
    primera version (el documento no tiene ninguna todavia), no hay nada que
    clonar: `content` y `signer` son obligatorios en ese caso (lo valida el
    controller, no este schema, porque la regla depende de si existe una
    version previa).
    """

    content: str | None = None
    signer: Signer | None = None
    change_notes: str | None = None
    file_base64: str | None = Field(
        default=None,
        description=FILE_BASE64_DESCRIPTION + " Al clonar, si se omite se hereda "
        "el archivo de la versión anterior.",
    )


class ConsentDocumentVersionUpdate(BaseModel):
    """Todos los campos opcionales: PATCH parcial. Solo se aplica si la
    version esta en `draft` (lo valida el controller via
    `VersioningService.ensure_draft`)."""

    content: str | None = None
    signer: Signer | None = None
    change_notes: str | None = None
    file_base64: str | None = Field(
        default=None,
        description=FILE_BASE64_DESCRIPTION + " Omitirlo no toca el archivo; "
        "`null` explícito lo quita.",
    )


class ConsentDocumentVersionWrite(BaseModel):
    """Interno (no sale en el OpenAPI): lo que se escribe en la version tras
    validar el archivo. Agrega los campos `file_*` que calcula la API."""

    content: str | None = None
    signer: Signer | None = None
    change_notes: str | None = None
    file_base64: str | None = None
    file_content_type: str | None = None
    file_sha256: str | None = None
    file_size_bytes: int | None = None


class ConsentDocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    consent_document_id: UUID
    version_number: int
    status: VersionStatus
    published_at: datetime | None
    change_notes: str | None
    content: str
    signer: Signer
    file_content_type: str | None = Field(
        description="Tipo del archivo (hoy solo `application/pdf`); `null` sin archivo."
    )
    file_sha256: str | None = Field(
        description="SHA-256 hex (minúscula) de los bytes del PDF; `null` sin archivo."
    )
    file_size_bytes: int | None = Field(
        description="Tamaño del PDF decodificado en bytes; `null` sin archivo."
    )
    created_at: datetime
    updated_at: datetime

    @computed_field(description="`true` si la versión tiene archivo PDF.")  # type: ignore[prop-decorator]
    @property
    def has_file(self) -> bool:
        return self.file_sha256 is not None


class ConsentDocumentVersionWithOwnerRead(ConsentDocumentVersionRead):
    """`GET /consent-document-versions/{id}`: la version mas su documento dueno."""

    owner: VersionOwnerRead


class ConsentDocumentFileRead(BaseModel):
    """Archivo de una version, con su contenido en base64."""

    content_type: str = Field(description="Siempre `application/pdf`.")
    sha256: str = Field(description="SHA-256 hex (minúscula) de los bytes del PDF.")
    size_bytes: int = Field(description="Tamaño del PDF decodificado en bytes.")
    base64: str = Field(description="El PDF en base64 estricto.")


class DataTreatmentConsentRead(BaseModel):
    """`GET /consent-documents/data-treatment/current`: el consentimiento
    general vigente para la app que registra las firmas."""

    document: ConsentDocumentRead
    version: ConsentDocumentVersionRead = Field(
        description="Versión publicada más reciente del documento."
    )
    file: ConsentDocumentFileRead | None = Field(
        description="Archivo de la versión; `null` si esa versión publicada "
        "no tiene archivo (datos anteriores a la carga de PDF)."
    )


__all__ = [
    "DATA_TREATMENT_TYPE",
    "DOCUMENT_TYPE_VALUES",
    "SIGNER_VALUES",
    "ConsentDocumentBase",
    "ConsentDocumentCreate",
    "ConsentDocumentFileRead",
    "ConsentDocumentRead",
    "ConsentDocumentUpdate",
    "ConsentDocumentVersionCreate",
    "ConsentDocumentVersionRead",
    "ConsentDocumentVersionUpdate",
    "ConsentDocumentVersionWithOwnerRead",
    "ConsentDocumentVersionWrite",
    "DataTreatmentConsentRead",
]
