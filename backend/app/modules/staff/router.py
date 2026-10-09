"""Rutas HTTP del modulo `staff`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.modules.staff import controller
from app.modules.staff.schemas import StaffCreate, StaffRead, StaffUpdate

router = APIRouter(tags=["staff"])


@router.get("", response_model=Page[StaffRead])
async def list_staff(
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[StaffRead]:
    return await controller.list_staff(session, pagination, active_filter, search)


@router.post(
    "",
    response_model=StaffRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_staff(
    data: StaffCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffRead:
    return await controller.create_staff(session, data)


@router.get("/{staff_id}", response_model=StaffRead, responses=error_responses(404))
async def get_staff(
    staff_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffRead:
    return await controller.get_staff(session, staff_id)


@router.patch(
    "/{staff_id}", response_model=StaffRead, responses=error_responses(404, 409, 422)
)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffRead:
    return await controller.update_staff(session, staff_id, data)
