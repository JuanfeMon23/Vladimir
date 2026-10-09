"""Esquemas Pydantic de entrada/salida del modulo `print_labels`.

Dos recursos: `PrintLabel` (catalogo) y `PrintLabelVersion` (contenido
versionado, ciclo `draft` -> `published` -> `retired`, ver
`app.core.versioning`). `PrintLabelVersionRead` siempre incluye `status`;
las reglas de que solo un `draft` es editable las aplica el controller, no
el schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr
from app.core.versioning import VersionOwnerRead, VersionStatus
from app.modules.print_labels.models import OUTPUT_FORMAT_VALUES

# Enum derivado del CHECK `output_format` de `models.py`.
OutputFormat = Literal[OUTPUT_FORMAT_VALUES]


class PrintLabelBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    description: str | None = None


class PrintLabelCreate(PrintLabelBase):
    is_active: bool = True


class PrintLabelUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class PrintLabelRead(PrintLabelBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PrintLabelVersionCreate(BaseModel):
    """Body de `POST /print-labels/{id}/versions`.

    Si la etiqueta ya tiene una version previa (publicada o retirada), el
    nuevo draft la clona y estos campos son overrides opcionales. Si es la
    primera version (la etiqueta no tiene ninguna todavia), no hay nada que
    clonar: todos salvo `barcode_type` y `change_notes` son obligatorios en
    ese caso (lo valida el controller, no este schema, porque la regla
    depende de si existe una version previa).
    """

    width_mm: float | None = None
    height_mm: float | None = None
    dpi: int | None = None
    output_format: OutputFormat | None = None
    barcode_type: str | None = Field(default=None, max_length=32)
    copies: int | None = None
    template_content: str | None = None
    placeholders: dict | None = None
    change_notes: str | None = None


class PrintLabelVersionUpdate(BaseModel):
    """Todos los campos opcionales: PATCH parcial. Solo se aplica si la
    version esta en `draft` (lo valida el controller via
    `VersioningService.ensure_draft`)."""

    width_mm: float | None = None
    height_mm: float | None = None
    dpi: int | None = None
    output_format: OutputFormat | None = None
    barcode_type: str | None = Field(default=None, max_length=32)
    copies: int | None = None
    template_content: str | None = None
    placeholders: dict | None = None
    change_notes: str | None = None


class PrintLabelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    print_label_id: UUID
    version_number: int
    status: VersionStatus
    published_at: datetime | None
    change_notes: str | None
    width_mm: float
    height_mm: float
    dpi: int
    output_format: OutputFormat
    barcode_type: str | None
    copies: int
    template_content: str
    placeholders: dict
    created_at: datetime
    updated_at: datetime


class PrintLabelVersionWithOwnerRead(PrintLabelVersionRead):
    """`GET /print-label-versions/{id}`: la version mas su etiqueta duena."""

    owner: VersionOwnerRead


__all__ = [
    "OUTPUT_FORMAT_VALUES",
    "PrintLabelBase",
    "PrintLabelCreate",
    "PrintLabelRead",
    "PrintLabelUpdate",
    "PrintLabelVersionCreate",
    "PrintLabelVersionRead",
    "PrintLabelVersionUpdate",
    "PrintLabelVersionWithOwnerRead",
]
