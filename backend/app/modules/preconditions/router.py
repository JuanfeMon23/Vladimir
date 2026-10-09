"""Rutas HTTP del modulo `preconditions`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.modules.preconditions import controller
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionRead,
    PreconditionUpdate,
)

router = APIRouter(tags=["preconditions"])


@router.get("", response_model=Page[PreconditionRead])
async def list_preconditions(
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[PreconditionRead]:
    """Precondiciones raiz, paginadas, cada una con sus items anidados."""
    return await controller.list_preconditions(
        session, pagination, active_filter, search
    )


@router.post(
    "",
    response_model=PreconditionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_precondition(
    data: PreconditionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    return await controller.create_precondition(session, data)


@router.get(
    "/{precondition_id}",
    response_model=PreconditionRead,
    responses=error_responses(404),
)
async def get_precondition(
    precondition_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    return await controller.get_precondition(session, precondition_id)


@router.patch(
    "/{precondition_id}",
    response_model=PreconditionRead,
    responses=error_responses(404, 409, 422),
)
async def update_precondition(
    precondition_id: UUID,
    data: PreconditionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    return await controller.update_precondition(session, precondition_id, data)


@router.post(
    "/{precondition_id}/items",
    response_model=PreconditionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_item(
    precondition_id: UUID,
    data: PreconditionItemCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    return await controller.create_item(session, precondition_id, data)
