"""Rutas HTTP del modulo `preconditions`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.modules.preconditions import controller
from app.modules.preconditions.permissions import (
    ADD_ITEM,
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    CanAddItem,
    CanCreate,
    CanView,
)
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionRead,
    PreconditionUpdate,
)

router = APIRouter(tags=["preconditions"])

ENTITY = "precondition"
# Campos auditados (sin timestamps ni items anidados).
AUDITED_FIELDS = {
    "code",
    "name",
    "description",
    "category",
    "duration_value",
    "duration_unit",
    "patient_instructions",
    "is_active",
}


def _snapshot(precondition: PreconditionRead) -> dict:
    return precondition.model_dump(include=AUDITED_FIELDS)


@router.get("", response_model=Page[PreconditionRead])
async def list_preconditions(
    _user: CanView,
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
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    created = await controller.create_precondition(session, data)
    await record_audit(
        CREATE, user, entity_type=ENTITY, entity_id=created.id, after=_snapshot(created)
    )
    return created


@router.get(
    "/{precondition_id}",
    response_model=PreconditionRead,
    responses=error_responses(404),
)
async def get_precondition(
    _user: CanView,
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
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = _snapshot(await controller.get_precondition(session, precondition_id))
    updated = await controller.update_precondition(session, precondition_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=ENTITY,
        entity_id=precondition_id,
        before=before,
        after=_snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@router.post(
    "/{precondition_id}/items",
    response_model=PreconditionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_item(
    precondition_id: UUID,
    data: PreconditionItemCreate,
    user: CanAddItem,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PreconditionRead:
    item = await controller.create_item(session, precondition_id, data)
    await record_audit(
        ADD_ITEM,
        user,
        entity_type=ENTITY,
        entity_id=item.id,
        after={**_snapshot(item), "parent_id": item.parent_id},
    )
    return item
