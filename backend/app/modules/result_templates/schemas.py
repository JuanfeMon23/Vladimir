"""Esquemas Pydantic de entrada/salida del modulo `result_templates`.

Recursos:
- Catalogos simples: `Unit` (UCUM), `Analyte`, `ResultOptionSet` +
  `ResultOption` (opciones dentro de un conjunto).
- Entidad versionada (mismo patron de `print_labels`, via
  `app.core.versioning`): `ResultTemplate` + `ResultTemplateVersion`.
- Contenido editable solo mientras la version este en `draft`:
  `ResultTemplateSection`, `ResultTemplateAnalyte`, `ReferenceRange`. Nada
  se borra: se desactiva con `is_active` en su PATCH.

Unidades (contrato con la app externa): la escritura es solo por id
(`default_unit_id` / `unit_id`); la lectura conserva el texto de siempre
(`default_unit` / `unit` = simbolo de la unidad) y agrega el objeto
completo en `default_unit_detail` / `unit_detail`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.schemas import ActivityReasonInput, CodeStr
from app.core.versioning import VersionOwnerRead, VersionStatus
from app.modules.result_templates.models import (
    AGE_UNIT_VALUES,
    RESULT_TYPE_VALUES,
    SEX_VALUES,
)

# Enums derivados de los CHECK de `models.py` (fuente unica de los valores).
ResultType = Literal[RESULT_TYPE_VALUES]
Sex = Literal[SEX_VALUES]
AgeUnit = Literal[AGE_UNIT_VALUES]

# --------------------------------------------------------------------------
# Units (UCUM)
# --------------------------------------------------------------------------


class UnitBase(BaseModel):
    code: CodeStr = Field(description="Codigo UCUM (distingue mayusculas).")
    symbol: str = Field(max_length=32)
    name: str = Field(max_length=150)


class UnitCreate(UnitBase):
    is_active: bool = True


class UnitUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    symbol: str | None = Field(default=None, max_length=32)
    name: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class UnitRead(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitSummary(BaseModel):
    """Unidad embebida en la lectura de analitos y analitos de plantilla."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    symbol: str
    name: str


# --------------------------------------------------------------------------
# Analytes
# --------------------------------------------------------------------------


class AnalyteBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    loinc_code: str | None = Field(default=None, max_length=32)
    description: str | None = None


class AnalyteCreate(AnalyteBase):
    default_unit_id: UUID | None = None
    is_active: bool = True


class AnalyteUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    loinc_code: str | None = Field(default=None, max_length=32)
    default_unit_id: UUID | None = None
    description: str | None = None
    is_active: bool | None = None


class AnalyteRead(AnalyteBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    default_unit_id: UUID | None
    default_unit: str | None = Field(
        default=None, description="Simbolo de la unidad (solo lectura)."
    )
    default_unit_detail: UnitSummary | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Result option sets + options
# --------------------------------------------------------------------------


class ResultOptionSetBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)


class ResultOptionSetCreate(ResultOptionSetBase):
    is_active: bool = True


class ResultOptionSetUpdate(ActivityReasonInput):
    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None


class ResultOptionSetRead(ResultOptionSetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResultOptionBase(BaseModel):
    code: CodeStr
    label: str = Field(max_length=150)
    sort_order: int
    is_abnormal: bool = False


class ResultOptionCreate(ResultOptionBase):
    is_active: bool = True


class ResultOptionUpdate(ActivityReasonInput):
    code: CodeStr | None = None
    label: str | None = Field(default=None, max_length=150)
    sort_order: int | None = None
    is_abnormal: bool | None = None
    is_active: bool | None = None


class ResultOptionRead(ResultOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    option_set_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Result templates + versions
# --------------------------------------------------------------------------


class ResultTemplateBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    description: str | None = None


class ResultTemplateCreate(ResultTemplateBase):
    is_active: bool = True


class ResultTemplateUpdate(ActivityReasonInput):
    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class ResultTemplateRead(ResultTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResultTemplateVersionCreate(BaseModel):
    """Body de `POST /result-templates/{id}/versions`.

    Si la plantilla ya tiene una version previa (publicada o retirada), el
    nuevo draft la clona (secciones, analitos y rangos ACTIVOS, ver
    `controller.create_version`) y `report_settings` es un override
    opcional. Si es la primera version, no hay nada que clonar:
    `report_settings` es obligatorio en ese caso (lo valida el controller).
    """

    report_settings: dict | None = None
    change_notes: str | None = None


class ResultTemplateVersionUpdate(BaseModel):
    """Todos los campos opcionales: PATCH parcial. Solo se aplica si la
    version esta en `draft` (ver `VersioningService.ensure_draft`)."""

    report_settings: dict | None = None
    change_notes: str | None = None


class ResultTemplateVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    result_template_id: UUID
    version_number: int
    status: VersionStatus
    published_at: datetime | None
    change_notes: str | None
    report_settings: dict
    created_at: datetime
    updated_at: datetime


class ResultTemplateVersionWithOwnerRead(ResultTemplateVersionRead):
    """`GET /result-template-versions/{id}`: la version mas su plantilla duena."""

    owner: VersionOwnerRead


# --------------------------------------------------------------------------
# Sections (editable solo en draft)
# --------------------------------------------------------------------------


class ResultTemplateSectionCreate(BaseModel):
    name: str = Field(max_length=150)
    sort_order: int


class ResultTemplateSectionUpdate(ActivityReasonInput):
    name: str | None = Field(default=None, max_length=150)
    sort_order: int | None = None
    is_active: bool | None = None


class ResultTemplateSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_id: UUID
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Template analytes (editable solo en draft)
# --------------------------------------------------------------------------


class ResultTemplateAnalyteCreate(BaseModel):
    section_id: UUID | None = None
    analyte_id: UUID
    sort_order: int
    result_type: ResultType
    unit_id: UUID | None = None
    decimals: int | None = None
    option_set_id: UUID | None = None
    formula: str | None = None
    is_required: bool = True
    is_reportable: bool = True
    default_value: str | None = Field(default=None, max_length=255)


class ResultTemplateAnalyteUpdate(ActivityReasonInput):
    section_id: UUID | None = None
    analyte_id: UUID | None = None
    sort_order: int | None = None
    result_type: ResultType | None = None
    unit_id: UUID | None = None
    decimals: int | None = None
    option_set_id: UUID | None = None
    formula: str | None = None
    is_required: bool | None = None
    is_reportable: bool | None = None
    default_value: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class ResultTemplateAnalyteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_id: UUID
    section_id: UUID | None
    analyte_id: UUID
    sort_order: int
    result_type: ResultType
    unit_id: UUID | None
    unit: str | None = Field(
        default=None, description="Simbolo de la unidad (solo lectura)."
    )
    unit_detail: UnitSummary | None = None
    decimals: int | None
    option_set_id: UUID | None
    formula: str | None
    is_required: bool
    is_reportable: bool
    default_value: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Reference ranges (editable solo en draft)
# --------------------------------------------------------------------------

# Pares (menor, mayor) espejo de los CHECK de `reference_ranges`; un extremo
# NULL no se compara (rango abierto).
REFERENCE_RANGE_BOUND_PAIRS = (
    ("low", "high"),
    ("critical_low", "low"),
    ("high", "critical_high"),
    ("age_min", "age_max"),
)


def reference_range_bound_errors(values: Mapping[str, Any]) -> list[str]:
    """Pares de limites invertidos (p. ej. `low` > `high`). Vacia = OK.

    La usan el validador de los schemas (cuerpo del request) y el
    controller (valores ya combinados con los guardados, en un PATCH)."""
    errors = []
    for lower, upper in REFERENCE_RANGE_BOUND_PAIRS:
        low_value, high_value = values.get(lower), values.get(upper)
        if low_value is not None and high_value is not None and low_value > high_value:
            errors.append(
                f"{lower} ({low_value}) debe ser menor o igual que "
                f"{upper} ({high_value})"
            )
    return errors


class _ReferenceRangeBounds(BaseModel):
    @model_validator(mode="after")
    def _bounds_in_order(self) -> Self:
        errors = reference_range_bound_errors(self.__dict__)
        if errors:
            raise ValueError("; ".join(errors))
        return self


class ReferenceRangeCreate(_ReferenceRangeBounds):
    sex: Sex = "any"
    age_min: float | None = None
    age_max: float | None = None
    age_unit: AgeUnit | None = None
    condition: str | None = Field(default=None, max_length=255)
    low: float | None = None
    high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    expected_option_id: UUID | None = None
    expected_boolean: bool | None = None
    display_text: str | None = Field(default=None, max_length=255)
    interpretation: str | None = None


class ReferenceRangeUpdate(_ReferenceRangeBounds, ActivityReasonInput):
    sex: Sex | None = None
    age_min: float | None = None
    age_max: float | None = None
    age_unit: AgeUnit | None = None
    condition: str | None = Field(default=None, max_length=255)
    low: float | None = None
    high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    expected_option_id: UUID | None = None
    expected_boolean: bool | None = None
    display_text: str | None = Field(default=None, max_length=255)
    interpretation: str | None = None
    is_active: bool | None = None


class ReferenceRangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_analyte_id: UUID
    sex: Sex
    age_min: float | None
    age_max: float | None
    age_unit: AgeUnit | None
    condition: str | None
    low: float | None
    high: float | None
    critical_low: float | None
    critical_high: float | None
    expected_option_id: UUID | None
    expected_boolean: bool | None
    display_text: str | None
    interpretation: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = [
    "AGE_UNIT_VALUES",
    "RESULT_TYPE_VALUES",
    "SEX_VALUES",
    "AnalyteBase",
    "AnalyteCreate",
    "AnalyteRead",
    "AnalyteUpdate",
    "ReferenceRangeCreate",
    "ReferenceRangeRead",
    "ReferenceRangeUpdate",
    "ResultOptionBase",
    "ResultOptionCreate",
    "ResultOptionRead",
    "ResultOptionSetBase",
    "ResultOptionSetCreate",
    "ResultOptionSetRead",
    "ResultOptionSetUpdate",
    "ResultOptionUpdate",
    "ResultTemplateAnalyteCreate",
    "ResultTemplateAnalyteRead",
    "ResultTemplateAnalyteUpdate",
    "ResultTemplateBase",
    "ResultTemplateCreate",
    "ResultTemplateRead",
    "ResultTemplateSectionCreate",
    "ResultTemplateSectionRead",
    "ResultTemplateSectionUpdate",
    "ResultTemplateUpdate",
    "ResultTemplateVersionCreate",
    "ResultTemplateVersionRead",
    "ResultTemplateVersionUpdate",
    "UnitCreate",
    "UnitRead",
    "UnitSummary",
    "UnitUpdate",
    "reference_range_bound_errors",
]
