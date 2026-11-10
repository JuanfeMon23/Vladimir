"""Esquemas de los catalogos de categoria expuestos en `/api/v1/catalogs/*`.

Todos comparten `id`, `code`, `name`, `sort_order` e `is_active` (`CategoryMixin`);
los que tienen columnas de comportamiento las agregan (`minutes`, banderas de
tipo de resultado, `is_wildcard`, `days`). El `code` se fija al crear y no se
edita: las demas tablas lo referencian por FK.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr


class CategoryCreate(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CategoryUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial. `code` no se edita."""

    name: str | None = Field(default=None, max_length=150)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- duration_units ---


class DurationUnitCreate(CategoryCreate):
    minutes: int = Field(gt=0, description="Minutos que equivale una unidad.")


class DurationUnitUpdate(CategoryUpdate):
    minutes: int | None = Field(default=None, gt=0)


class DurationUnitRead(CategoryRead):
    minutes: int = Field(description="Minutos que equivale una unidad.")


# --- result_types ---


class ResultTypeBehavior(BaseModel):
    """Banderas que gobiernan que admite y exige un tipo de resultado."""

    uses_option_set: bool = Field(
        description="El valor se elige de un conjunto de opciones: el analito "
        "exige `option_set_id` y el rango admite `expected_option_id`."
    )
    uses_numeric_range: bool = Field(
        description="El rango admite `low`, `high`, `critical_low` y `critical_high`."
    )
    uses_boolean_range: bool = Field(description="El rango admite `expected_boolean`.")
    uses_unit: bool = Field(
        description="`unit_id` y `decimals` son obligatorios para publicar."
    )
    uses_formula: bool = Field(description="`formula` es obligatoria para publicar.")
    requires_reference_range: bool = Field(
        description="Si el analito es reportable, exige al menos un rango "
        "activo para publicar."
    )


class ResultTypeCreate(ResultTypeBehavior, CategoryCreate):
    pass


class ResultTypeUpdate(CategoryUpdate):
    uses_option_set: bool | None = None
    uses_numeric_range: bool | None = None
    uses_boolean_range: bool | None = None
    uses_unit: bool | None = None
    uses_formula: bool | None = None
    requires_reference_range: bool | None = None


class ResultTypeRead(ResultTypeBehavior, CategoryRead):
    pass


# --- sexes ---


class SexCreate(CategoryCreate):
    is_wildcard: bool = Field(
        default=False,
        description="Fila comodin («cualquiera»): coincide con todos los "
        "sexos al comprobar solapamientos. A lo sumo una.",
    )


class SexUpdate(CategoryUpdate):
    is_wildcard: bool | None = None


class SexRead(CategoryRead):
    is_wildcard: bool = Field(
        description="Fila comodin («cualquiera»): coincide con todos los sexos."
    )


# --- age_units ---


class AgeUnitCreate(CategoryCreate):
    days: float = Field(gt=0, description="Dias que equivale una unidad.")


class AgeUnitUpdate(CategoryUpdate):
    days: float | None = Field(default=None, gt=0)


class AgeUnitRead(CategoryRead):
    days: float = Field(description="Dias que equivale una unidad.")
