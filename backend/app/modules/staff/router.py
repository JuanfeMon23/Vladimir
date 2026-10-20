"""Rutas HTTP del modulo `staff`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.core.leo import audit_patch, auth, authorize_patch, record_audit
from app.core.schemas import Page, error_responses
from app.modules.staff import controller
from app.modules.staff.permissions import (
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    CanCreate,
    CanView,
)
from app.modules.staff.schemas import StaffCreate, StaffRead, StaffUpdate

router = APIRouter(tags=["staff"])

ENTITY = "staff"
# Campos auditados (sin timestamps).
AUDITED_FIELDS = {
    "document_type",
    "document_number",
    "first_name",
    "last_name",
    "email",
    "phone",
    "job_title",
    "professional_license",
    "is_active",
}


def _snapshot(person: StaffRead) -> dict:
    return person.model_dump(include=AUDITED_FIELDS)


@router.get("", response_model=Page[StaffRead])
async def list_staff(
    _user: CanView,
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
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffRead:
    created = await controller.create_staff(session, data)
    await record_audit(
        CREATE, user, entity_type=ENTITY, entity_id=created.id, after=_snapshot(created)
    )
    return created


@router.get("/{staff_id}", response_model=StaffRead, responses=error_responses(404))
async def get_staff(
    _user: CanView,
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
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StaffRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = _snapshot(await controller.get_staff(session, staff_id))
    updated = await controller.update_staff(session, staff_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=ENTITY,
        entity_id=staff_id,
        before=before,
        after=_snapshot(updated),
        reason=data.activity_reason,
    )
    return updated
