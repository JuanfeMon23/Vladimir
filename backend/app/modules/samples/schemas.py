"""Esquemas Pydantic de entrada/salida del modulo `samples`.

Dos recursos en relacion 1:N: `Sample` (muestra, catalogo) y `SampleType`
(tipo de tubo/recipiente de toma, catalogo). `sample_id` nunca se recibe del
cliente en `SampleTypeCreate`: lo fija el endpoint
`POST /samples/{sample_id}/types`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr
from app.modules.samples.models import SPECIMEN_VALUES

# Enum derivado del CHECK `specimen` de `models.py`.
Specimen = Literal[SPECIMEN_VALUES]


class SampleBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    description: str | None = None


class SampleCreate(SampleBase):
    is_active: bool = True


class SampleUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class SampleTypeBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    cap_color_hex: str | None = Field(default=None, max_length=7)
    additive: str | None = Field(default=None, max_length=100)
    specimen: Specimen
    volume_ml: float | None = None
    storage_temperature: str | None = Field(default=None, max_length=32)
    stability_hours: int | None = None
    draw_order: int | None = None
    collection_instructions: str | None = None


class SampleTypeCreate(SampleTypeBase):
    """Body de `POST /samples/{sample_id}/types`."""

    is_active: bool = True


class SampleTypeUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial.

    No incluye `sample_id`: la muestra a la que pertenece un tipo no se
    reasigna por este endpoint.
    """

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    cap_color_hex: str | None = Field(default=None, max_length=7)
    additive: str | None = Field(default=None, max_length=100)
    specimen: Specimen | None = None
    volume_ml: float | None = None
    storage_temperature: str | None = Field(default=None, max_length=32)
    stability_hours: int | None = None
    draw_order: int | None = None
    collection_instructions: str | None = None
    is_active: bool | None = None


class SampleTypeRead(SampleTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SampleRead(SampleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    types: list[SampleTypeRead] = []


__all__ = [
    "SPECIMEN_VALUES",
    "SampleBase",
    "SampleCreate",
    "SampleRead",
    "SampleTypeBase",
    "SampleTypeCreate",
    "SampleTypeRead",
    "SampleTypeUpdate",
    "SampleUpdate",
]
