"""Rutas HTTP del modulo `lab_areas`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.core.leo import auth, record_audit
from app.core.schemas import Page, error_responses
from app.modules.lab_areas import controller
from app.modules.lab_areas.permissions import (
    ASSIGN_MANAGER,
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    CanAssignManager,
    CanCreate,
    CanView,
)
from app.modules.lab_areas.schemas import (
    LabAreaCreate,
    LabAreaRead,
    LabAreaUpdate,
    ManagerAssignmentCreate,
    ManagerAssignmentRead,
)

router = APIRouter(tags=["lab_areas"])

ENTITY = "lab_area"
# Campos auditados (sin timestamps ni el encargado, que tiene su propio evento).
AUDITED_FIELDS = {"code", "name", "description", "is_active"}


def _snapshot(area: LabAreaRead) -> dict:
    return area.model_dump(include=AUDITED_FIELDS)


@router.get("", response_model=Page[LabAreaRead])
async def list_lab_areas(
    _user: CanView,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[LabAreaRead]:
    return await controller.list_lab_areas(session, pagination, active_filter, search)


@router.post(
    "",
    response_model=LabAreaRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_lab_area(
    data: LabAreaCreate,
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabAreaRead:
    created = await controller.create_lab_area(session, data)
    await record_audit(
        CREATE,
        user,
        entity_type=ENTITY,
        entity_id=created.id,
        after=_snapshot(created),
    )
    return created


@router.get("/{area_id}", response_model=LabAreaRead, responses=error_responses(404))
async def get_lab_area(
    _user: CanView,
    area_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabAreaRead:
    return await controller.get_lab_area(session, area_id)


@router.patch(
    "/{area_id}", response_model=LabAreaRead, responses=error_responses(404, 409, 422)
)
async def update_lab_area(
    area_id: UUID,
    data: LabAreaUpdate,
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabAreaRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    sent = data.model_fields_set
    changes_status = "is_active" in sent and data.is_active is not None
    changes_data = bool(sent - {"is_active", "activity_reason"}) or not changes_status
    if changes_data:
        await EDIT_CHECK(request, user)
    if changes_status:
        await CHANGE_STATUS_CHECK(request, user)

    before = _snapshot(await controller.get_lab_area(session, area_id))
    updated = await controller.update_lab_area(session, area_id, data)
    after = _snapshot(updated)
    status_changed = before["is_active"] != after["is_active"]
    data_before = {k: v for k, v in before.items() if k != "is_active"}
    data_after = {k: v for k, v in after.items() if k != "is_active"}
    if data_before != data_after:
        await record_audit(
            EDIT,
            user,
            entity_type=ENTITY,
            entity_id=area_id,
            before=data_before,
            after=data_after,
        )
    if status_changed:
        await record_audit(
            CHANGE_STATUS,
            user,
            entity_type=ENTITY,
            entity_id=area_id,
            before={"is_active": before["is_active"]},
            after={"is_active": after["is_active"]},
            reason=data.activity_reason,
        )
    return updated


@router.put(
    "/{area_id}/manager",
    response_model=ManagerAssignmentRead,
    responses=error_responses(404, 422),
)
async def assign_manager(
    area_id: UUID,
    data: ManagerAssignmentCreate,
    user: CanAssignManager,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ManagerAssignmentRead:
    assignment = await controller.assign_manager(session, area_id, data)
    await record_audit(
        ASSIGN_MANAGER,
        user,
        entity_type="lab_area_manager_assignment",
        entity_id=assignment.id,
        after={
            "area_id": assignment.area_id,
            "staff_id": assignment.staff_id,
            "start_at": assignment.start_at,
            "notes": assignment.notes,
        },
    )
    return assignment


@router.get(
    "/{area_id}/manager-history",
    response_model=list[ManagerAssignmentRead],
    responses=error_responses(404),
)
async def get_manager_history(
    _user: CanView,
    area_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ManagerAssignmentRead]:
    return await controller.get_manager_history(session, area_id)
