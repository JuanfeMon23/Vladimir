"""Esquemas Pydantic de entrada/salida del modulo `preconditions`.

La jerarquia tiene un solo nivel (ver `models.py` / trigger de BD): una
precondicion raiz (`parent_id IS NULL`, `kind="precondition"`) agrupa items
(`kind="condition"`). `kind` y `parent_id` nunca se reciben del cliente: los
fija el endpoint que se use (`POST /preconditions` siempre crea una raiz,
`POST /preconditions/{id}/items` siempre crea un item bajo ese padre).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr

# `category`, `duration_unit` y `kind` son `code` de los catalogos
# `precondition_categories`, `duration_units` y `precondition_kinds`: el
# controller valida contra la BD las referencias nuevas.
Category = Annotated[str, Field(max_length=32)]
DurationUnit = Annotated[str, Field(max_length=16)]
Kind = Annotated[str, Field(max_length=16)]


class PreconditionBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    description: str | None = None
    category: Category
    duration_value: float | None = None
    duration_unit: DurationUnit | None = None
    patient_instructions: str | None = None


class PreconditionCreate(PreconditionBase):
    """Body de `POST /preconditions`: siempre crea una precondicion raiz."""

    is_active: bool = True


class PreconditionItemCreate(PreconditionBase):
    """Body de `POST /preconditions/{id}/items`: crea un item bajo esa raiz."""

    is_active: bool = True


class PreconditionUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial.

    No incluye `parent_id` ni `kind`: la jerarquia de un nodo no se
    reasigna por este endpoint.
    """

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    category: Category | None = None
    duration_value: float | None = None
    duration_unit: DurationUnit | None = None
    patient_instructions: str | None = None
    is_active: bool | None = None


class PreconditionRead(PreconditionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    kind: Kind
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[PreconditionRead] | None = None


__all__ = [
    "PreconditionBase",
    "PreconditionCreate",
    "PreconditionItemCreate",
    "PreconditionRead",
    "PreconditionUpdate",
]
