"""Rutas HTTP del modulo `lab_tests`. Delgadas: solo traducen HTTP <-> controller."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from leo_sdk import LeoUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import (
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
    active_only_filter,
    include_inactive_param,
    pagination_params,
    search_filter,
)
from app.core.leo import audit_patch, auth, authorize_patch, record_audit
from app.core.schemas import Page, error_responses
from app.modules.lab_tests import controller
from app.modules.lab_tests.permissions import (
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    SET_CONSENT_DOCUMENTS,
    SET_PRECONDITIONS,
    SET_SAMPLE_TYPES,
    CanCreate,
    CanSetConsentDocuments,
    CanSetPreconditions,
    CanSetSampleTypes,
    CanView,
)
from app.modules.lab_tests.schemas import (
    LabTestConsentDocumentInput,
    LabTestConsentDocumentRead,
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestPreconditionRead,
    LabTestRead,
    LabTestSampleTypeInput,
    LabTestSampleTypeRead,
    LabTestUpdate,
)

router = APIRouter(tags=["lab_tests"])

ENTITY = "lab_test"
# Campos auditados del examen (sin timestamps ni los conjuntos anidados, que
# tienen su propio evento).
AUDITED_FIELDS = {
    "code",
    "name",
    "abbreviation",
    "description",
    "area_id",
    "method",
    "turnaround_hours",
    "loinc_code",
    "cups_code",
    "is_active",
    "print_label_version_id",
    "result_template_version_id",
}
# Campos auditados de cada conjunto (sin id de fila ni estado derivado).
PRECONDITION_FIELDS = {
    "precondition_id",
    "is_mandatory",
    "sort_order",
    "name_override",
    "description_override",
    "duration_value_override",
    "duration_unit_override",
    "patient_instructions_override",
}
SAMPLE_TYPE_FIELDS = {
    "sample_type_id",
    "is_preferred",
    "required_volume_ml",
    "sort_order",
}
CONSENT_FIELDS = {"consent_document_version_id", "is_mandatory"}


def _snapshot(lab_test: LabTestRead) -> dict:
    return lab_test.model_dump(include=AUDITED_FIELDS)


def _rows(items: list, fields: set[str]) -> list[dict]:
    """Conjunto de filas activas como lista de dicts JSON, ordenada de forma estable."""
    rows = [item.model_dump(mode="json", include=fields) for item in items]
    return sorted(rows, key=lambda row: str(sorted(row.items())))


@router.get("", response_model=Page[LabTestRead])
async def list_lab_tests(
    _user: CanView,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
    area_id: Annotated[UUID | None, Query()] = None,
) -> Page[LabTestRead]:
    return await controller.list_lab_tests(
        session, pagination, active_filter, area_id, search
    )


@router.post(
    "",
    response_model=LabTestRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_lab_test(
    data: LabTestCreate,
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestRead:
    created = await controller.create_lab_test(session, data)
    await record_audit(
        CREATE,
        user,
        entity_type=ENTITY,
        entity_id=created.id,
        after={
            **_snapshot(created),
            "preconditions": _rows(created.preconditions, PRECONDITION_FIELDS),
            "sample_types": _rows(created.sample_types, SAMPLE_TYPE_FIELDS),
            "consent_documents": _rows(created.consent_documents, CONSENT_FIELDS),
        },
    )
    return created


@router.get(
    "/{lab_test_id}", response_model=LabTestRead, responses=error_responses(404)
)
async def get_lab_test(
    _user: CanView,
    lab_test_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestRead:
    """Detalle completo: precondiciones, tipos de muestra y documentos
    embebidos (ver `LabTestRead` / `controller.get_lab_test`)."""
    return await controller.get_lab_test(session, lab_test_id)


@router.patch(
    "/{lab_test_id}",
    response_model=LabTestRead,
    responses=error_responses(404, 409, 422),
)
async def update_lab_test(
    lab_test_id: UUID,
    data: LabTestUpdate,
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = _snapshot(await controller.get_lab_test(session, lab_test_id))
    updated = await controller.update_lab_test(session, lab_test_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=ENTITY,
        entity_id=lab_test_id,
        before=before,
        after=_snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@router.get(
    "/{lab_test_id}/preconditions",
    response_model=list[LabTestPreconditionRead],
    responses=error_responses(404),
)
async def get_lab_test_preconditions(
    _user: CanView,
    lab_test_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: Annotated[bool, Depends(include_inactive_param)],
) -> list[LabTestPreconditionRead]:
    """Solo las activas, salvo `?include_inactive=true`."""
    return await controller.get_preconditions(
        session, lab_test_id, include_inactive=include_inactive
    )


@router.put(
    "/{lab_test_id}/preconditions",
    response_model=list[LabTestPreconditionRead],
    responses=error_responses(404, 422),
)
async def set_lab_test_preconditions(
    lab_test_id: UUID,
    items: list[LabTestPreconditionInput],
    user: CanSetPreconditions,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestPreconditionRead]:
    """Reemplaza el set completo: lo quitado se desactiva, lo que vuelve se
    reactiva. 422 `inactive_reference` si se AGREGA una precondicion inactiva."""
    before = await controller.get_preconditions(session, lab_test_id)
    result = await controller.set_preconditions(session, lab_test_id, items)
    await record_audit(
        SET_PRECONDITIONS,
        user,
        entity_type=ENTITY,
        entity_id=lab_test_id,
        before={"preconditions": _rows(before, PRECONDITION_FIELDS)},
        after={"preconditions": _rows(result, PRECONDITION_FIELDS)},
    )
    return result


@router.get(
    "/{lab_test_id}/sample-types",
    response_model=list[LabTestSampleTypeRead],
    responses=error_responses(404),
)
async def get_lab_test_sample_types(
    _user: CanView,
    lab_test_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: Annotated[bool, Depends(include_inactive_param)],
) -> list[LabTestSampleTypeRead]:
    """Solo las activas, salvo `?include_inactive=true`."""
    return await controller.get_sample_types(
        session, lab_test_id, include_inactive=include_inactive
    )


@router.put(
    "/{lab_test_id}/sample-types",
    response_model=list[LabTestSampleTypeRead],
    responses=error_responses(404, 422),
)
async def set_lab_test_sample_types(
    lab_test_id: UUID,
    items: list[LabTestSampleTypeInput],
    user: CanSetSampleTypes,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestSampleTypeRead]:
    """Reemplaza el set completo de tipos de muestra del examen. Exige
    exactamente un `is_preferred=true` en el body (422 si no)."""
    before = await controller.get_sample_types(session, lab_test_id)
    result = await controller.set_sample_types(session, lab_test_id, items)
    await record_audit(
        SET_SAMPLE_TYPES,
        user,
        entity_type=ENTITY,
        entity_id=lab_test_id,
        before={"sample_types": _rows(before, SAMPLE_TYPE_FIELDS)},
        after={"sample_types": _rows(result, SAMPLE_TYPE_FIELDS)},
    )
    return result


@router.get(
    "/{lab_test_id}/consent-documents",
    response_model=list[LabTestConsentDocumentRead],
    responses=error_responses(404),
)
async def get_lab_test_consent_documents(
    _user: CanView,
    lab_test_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: Annotated[bool, Depends(include_inactive_param)],
) -> list[LabTestConsentDocumentRead]:
    """Solo las activas, salvo `?include_inactive=true`."""
    return await controller.get_consent_documents(
        session, lab_test_id, include_inactive=include_inactive
    )


@router.put(
    "/{lab_test_id}/consent-documents",
    response_model=list[LabTestConsentDocumentRead],
    responses=error_responses(404, 422),
)
async def set_lab_test_consent_documents(
    lab_test_id: UUID,
    items: list[LabTestConsentDocumentInput],
    user: CanSetConsentDocuments,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestConsentDocumentRead]:
    """Reemplaza el set completo (lo quitado se desactiva). 422
    `inactive_reference` si se AGREGA una version de un documento inactivo."""
    before = await controller.get_consent_documents(session, lab_test_id)
    result = await controller.set_consent_documents(session, lab_test_id, items)
    await record_audit(
        SET_CONSENT_DOCUMENTS,
        user,
        entity_type=ENTITY,
        entity_id=lab_test_id,
        before={"consent_documents": _rows(before, CONSENT_FIELDS)},
        after={"consent_documents": _rows(result, CONSENT_FIELDS)},
    )
    return result
