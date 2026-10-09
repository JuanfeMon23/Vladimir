"""Rutas HTTP del modulo `lab_tests`. Delgadas: solo traducen HTTP <-> controller."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
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
from app.core.schemas import Page, error_responses
from app.modules.lab_tests import controller
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


@router.get("", response_model=Page[LabTestRead])
async def list_lab_tests(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestRead:
    return await controller.create_lab_test(session, data)


@router.get(
    "/{lab_test_id}", response_model=LabTestRead, responses=error_responses(404)
)
async def get_lab_test(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestRead:
    return await controller.update_lab_test(session, lab_test_id, data)


@router.get(
    "/{lab_test_id}/preconditions",
    response_model=list[LabTestPreconditionRead],
    responses=error_responses(404),
)
async def get_lab_test_preconditions(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestPreconditionRead]:
    """Reemplaza el set completo: lo quitado se desactiva, lo que vuelve se
    reactiva. 422 `inactive_reference` si se AGREGA una precondicion inactiva."""
    return await controller.set_preconditions(session, lab_test_id, items)


@router.get(
    "/{lab_test_id}/sample-types",
    response_model=list[LabTestSampleTypeRead],
    responses=error_responses(404),
)
async def get_lab_test_sample_types(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestSampleTypeRead]:
    """Reemplaza el set completo de tipos de muestra del examen. Exige
    exactamente un `is_preferred=true` en el body (422 si no)."""
    return await controller.set_sample_types(session, lab_test_id, items)


@router.get(
    "/{lab_test_id}/consent-documents",
    response_model=list[LabTestConsentDocumentRead],
    responses=error_responses(404),
)
async def get_lab_test_consent_documents(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LabTestConsentDocumentRead]:
    """Reemplaza el set completo (lo quitado se desactiva). 422
    `inactive_reference` si se AGREGA una version de un documento inactivo."""
    return await controller.set_consent_documents(session, lab_test_id, items)
