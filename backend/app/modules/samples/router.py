"""Rutas HTTP del modulo `samples`. Delgadas: solo traducen HTTP <-> controller.

Dos routers: `router` (recurso `samples`, registrado en
`/api/v1/samples`) y `sample_types_router` (recurso `sample-types`,
registrado en `/api/v1/sample-types`) para `PATCH /sample-types/{id}`, que
edita un tipo directamente como recurso de nivel superior.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import (
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
    active_only_filter,
    pagination_params,
    search_filter,
)
from app.core.schemas import Page, error_responses
from app.modules.samples import controller
from app.modules.samples.schemas import (
    SampleCreate,
    SampleRead,
    SampleTypeCreate,
    SampleTypeRead,
    SampleTypeUpdate,
    SampleUpdate,
)

router = APIRouter(tags=["samples"])
sample_types_router = APIRouter(tags=["samples"])


@router.get("", response_model=Page[SampleRead])
async def list_samples(
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[SampleRead]:
    """Muestras, paginadas, cada una con sus tipos anidados."""
    return await controller.list_samples(session, pagination, active_filter, search)


@router.post(
    "",
    response_model=SampleRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_sample(
    data: SampleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleRead:
    return await controller.create_sample(session, data)


@router.get("/{sample_id}", response_model=SampleRead, responses=error_responses(404))
async def get_sample(
    sample_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleRead:
    return await controller.get_sample(session, sample_id)


@router.patch(
    "/{sample_id}", response_model=SampleRead, responses=error_responses(404, 409, 422)
)
async def update_sample(
    sample_id: UUID,
    data: SampleUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleRead:
    return await controller.update_sample(session, sample_id, data)


@router.get(
    "/{sample_id}/types",
    response_model=Page[SampleTypeRead],
    responses=error_responses(404),
)
async def list_sample_types(
    sample_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[SampleTypeRead]:
    return await controller.list_sample_types(
        session, sample_id, pagination, active_filter, search
    )


@router.post(
    "/{sample_id}/types",
    response_model=SampleTypeRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_sample_type(
    sample_id: UUID,
    data: SampleTypeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleTypeRead:
    return await controller.create_sample_type(session, sample_id, data)


@sample_types_router.patch(
    "/{sample_type_id}",
    response_model=SampleTypeRead,
    responses=error_responses(404, 409, 422),
)
async def update_sample_type(
    sample_type_id: UUID,
    data: SampleTypeUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleTypeRead:
    return await controller.update_sample_type(session, sample_type_id, data)
