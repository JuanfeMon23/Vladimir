"""Rutas HTTP del modulo `samples`. Delgadas: solo traducen HTTP <-> controller.

Dos routers: `router` (recurso `samples`, registrado en
`/api/v1/samples`) y `sample_types_router` (recurso `sample-types`,
registrado en `/api/v1/sample-types`) para `PATCH /sample-types/{id}`, que
edita un tipo directamente como recurso de nivel superior.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from leo_sdk import LeoUser
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
from app.core.leo import audit_patch, auth, authorize_patch, record_audit, snapshot
from app.core.schemas import Page, error_responses
from app.modules.samples import controller
from app.modules.samples.permissions import (
    ADD_TYPE,
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    CanAddType,
    CanCreate,
    CanView,
)
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

ENTITY = "sample"
TYPE_ENTITY = "sample_type"


def _snapshot(sample: SampleRead) -> dict:
    return snapshot(sample, "types")  # los tipos tienen sus propios eventos


@router.get("", response_model=Page[SampleRead])
async def list_samples(
    _user: CanView,
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
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleRead:
    created = await controller.create_sample(session, data)
    await record_audit(
        CREATE, user, entity_type=ENTITY, entity_id=created.id, after=_snapshot(created)
    )
    return created


@router.get("/{sample_id}", response_model=SampleRead, responses=error_responses(404))
async def get_sample(
    _user: CanView,
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
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = _snapshot(await controller.get_sample(session, sample_id))
    updated = await controller.update_sample(session, sample_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=ENTITY,
        entity_id=sample_id,
        before=before,
        after=_snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@router.get(
    "/{sample_id}/types",
    response_model=Page[SampleTypeRead],
    responses=error_responses(404),
)
async def list_sample_types(
    _user: CanView,
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
    user: CanAddType,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleTypeRead:
    created = await controller.create_sample_type(session, sample_id, data)
    await record_audit(
        ADD_TYPE,
        user,
        entity_type=TYPE_ENTITY,
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@sample_types_router.patch(
    "/{sample_type_id}",
    response_model=SampleTypeRead,
    responses=error_responses(404, 409, 422),
)
async def update_sample_type(
    sample_type_id: UUID,
    data: SampleTypeUpdate,
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SampleTypeRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = snapshot(await controller.get_sample_type(session, sample_type_id))
    updated = await controller.update_sample_type(session, sample_type_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=TYPE_ENTITY,
        entity_id=sample_type_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated
