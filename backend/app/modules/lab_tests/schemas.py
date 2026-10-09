"""Esquemas Pydantic de entrada/salida del modulo `lab_tests`.

Un examen (`LabTest`) es el catalogo central; sus tres colecciones hijas
(`lab_test_preconditions`, `lab_test_sample_types`,
`lab_test_consent_documents`) se gestionan como *set completo*: cada
`PUT /lab-tests/{id}/<coleccion>` deja activas exactamente las filas del
body. Nada se borra: lo quitado se desactiva (`is_active=false`) y lo que
vuelve reactiva su misma fila (ver `core.repository.sync_collection`). Los
`GET` devuelven solo las activas salvo `?include_inactive=true`.

`LabTestRead` distingue dos niveles de detalle, igual costo que pagar la
resolucion de overrides en cada fila de un listado:
- Listado (`GET /lab-tests`): solo los campos propios del examen; las tres
  colecciones quedan en `[]` (no se resuelven, evita N+1 en paginacion).
- Detalle (`GET /lab-tests/{id}`): las tres colecciones vienen embebidas,
  con el valor efectivo ya resuelto (ver `controller._resolve_precondition`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr
from app.modules.lab_tests.models import DURATION_UNIT_VALUES

# Enum derivado del CHECK `duration_unit_override` de `models.py`.
DurationUnit = Literal[DURATION_UNIT_VALUES]


class LabTestSampleTypeInput(BaseModel):
    """Tipo de muestra (recipiente) del examen. Se usa en
    `POST /lab-tests` (`sample_types`) y como elemento del body de
    `PUT /lab-tests/{id}/sample-types` (reemplaza el set completo). El set
    debe tener al menos un elemento y exactamente un `is_preferred=true`
    (lo valida el controller, no este schema, porque es una regla sobre el
    conjunto completo, no sobre una fila)."""

    sample_type_id: UUID
    is_preferred: bool = False
    required_volume_ml: float | None = None
    sort_order: int


class LabTestBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=150)
    abbreviation: str | None = Field(default=None, max_length=32)
    description: str | None = None
    area_id: UUID
    method: str | None = Field(default=None, max_length=150)
    turnaround_hours: int | None = None
    loinc_code: str | None = Field(default=None, max_length=32)
    cups_code: str | None = Field(default=None, max_length=32)


class LabTestCreate(LabTestBase):
    """`sample_types` es obligatorio: un examen siempre nace con al menos un
    tipo de muestra y exactamente uno preferido (lo valida el controller, que
    comparte la logica con `PUT /lab-tests/{id}/sample-types`)."""

    is_active: bool = True
    print_label_version_id: UUID | None = None
    result_template_version_id: UUID | None = None
    sample_types: list[LabTestSampleTypeInput]


class LabTestUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=150)
    abbreviation: str | None = Field(default=None, max_length=32)
    description: str | None = None
    area_id: UUID | None = None
    method: str | None = Field(default=None, max_length=150)
    turnaround_hours: int | None = None
    loinc_code: str | None = Field(default=None, max_length=32)
    cups_code: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    print_label_version_id: UUID | None = None
    result_template_version_id: UUID | None = None


# --- Precondiciones del examen (`PUT /lab-tests/{id}/preconditions`) ---


class LabTestPreconditionInput(BaseModel):
    """Un elemento del body: reemplaza el set completo."""

    precondition_id: UUID
    is_mandatory: bool = True
    sort_order: int
    name_override: str | None = Field(default=None, max_length=150)
    description_override: str | None = None
    duration_value_override: float | None = None
    duration_unit_override: DurationUnit | None = None
    patient_instructions_override: str | None = None


class LabTestPreconditionRead(BaseModel):
    """Precondicion asignada al examen, con el valor efectivo ya resuelto
    (override si existe, si no el del catalogo `preconditions`) y, aparte,
    los `*_override` crudos guardados en la fila de asignacion (`null` =
    sin override; el editor los usa sin reconstruirlos). `id` es el de la
    fila de asignacion (para `/activity`), no el de la precondicion."""

    id: UUID
    precondition_id: UUID
    is_mandatory: bool
    sort_order: int
    is_active: bool
    name: str
    description: str | None
    duration_value: float | None
    duration_unit: DurationUnit | None
    patient_instructions: str | None
    name_override: str | None
    description_override: str | None
    duration_value_override: float | None
    duration_unit_override: DurationUnit | None
    patient_instructions_override: str | None


# --- Tipos de muestra del examen (`PUT /lab-tests/{id}/sample-types`) ---


class LabTestSampleTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sample_type_id: UUID
    is_preferred: bool
    required_volume_ml: float | None
    sort_order: int
    is_active: bool


# --- Documentos a firmar del examen (`PUT /lab-tests/{id}/consent-documents`) ---


class LabTestConsentDocumentInput(BaseModel):
    """Un elemento del body: reemplaza el set completo. La version
    referenciada debe estar `published` (lo valida el controller)."""

    consent_document_version_id: UUID
    is_mandatory: bool = True


class LabTestConsentDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    consent_document_version_id: UUID
    is_mandatory: bool
    is_active: bool


class LabTestRead(LabTestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    print_label_version_id: UUID | None
    result_template_version_id: UUID | None
    created_at: datetime
    updated_at: datetime
    preconditions: list[LabTestPreconditionRead] = []
    sample_types: list[LabTestSampleTypeRead] = []
    consent_documents: list[LabTestConsentDocumentRead] = []


__all__ = [
    "LabTestBase",
    "LabTestConsentDocumentInput",
    "LabTestConsentDocumentRead",
    "LabTestCreate",
    "LabTestPreconditionInput",
    "LabTestPreconditionRead",
    "LabTestRead",
    "LabTestSampleTypeInput",
    "LabTestSampleTypeRead",
    "LabTestUpdate",
]
