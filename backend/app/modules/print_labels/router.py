"""Rutas HTTP del modulo `print_labels`. Delgadas: solo traducen HTTP <-> controller."""

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
    version_status_param,
)
from app.core.leo import audit_patch, auth, authorize_patch, record_audit, snapshot
from app.core.schemas import Page, error_responses
from app.core.versioning import RETIRE_VERSION_RESPONSES, VersionStatus
from app.modules.print_labels import controller
from app.modules.print_labels.permissions import (
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    CREATE_VERSION,
    EDIT,
    EDIT_CHECK,
    EDIT_VERSION,
    PUBLISH_VERSION,
    RETIRE_VERSION,
    CanCreate,
    CanCreateVersion,
    CanEditVersion,
    CanPublishVersion,
    CanRetireVersion,
    CanView,
)
from app.modules.print_labels.schemas import (
    PrintLabelCreate,
    PrintLabelRead,
    PrintLabelUpdate,
    PrintLabelVersionCreate,
    PrintLabelVersionRead,
    PrintLabelVersionUpdate,
    PrintLabelVersionWithOwnerRead,
)

router = APIRouter(tags=["print_labels"])
versions_router = APIRouter(tags=["print_labels"])

ENTITY = "print_label"
VERSION_ENTITY = "print_label_version"


@router.get("", response_model=Page[PrintLabelRead])
async def list_print_labels(
    _user: CanView,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[PrintLabelRead]:
    return await controller.list_labels(session, pagination, active_filter, search)


@router.post(
    "",
    response_model=PrintLabelRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_print_label(
    data: PrintLabelCreate,
    user: CanCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelRead:
    created = await controller.create_label(session, data)
    await record_audit(
        CREATE,
        user,
        entity_type=ENTITY,
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@router.get(
    "/{print_label_id}", response_model=PrintLabelRead, responses=error_responses(404)
)
async def get_print_label(
    _user: CanView,
    print_label_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelRead:
    return await controller.get_label(session, print_label_id)


@router.patch(
    "/{print_label_id}",
    response_model=PrintLabelRead,
    responses=error_responses(404, 409, 422),
)
async def update_print_label(
    print_label_id: UUID,
    data: PrintLabelUpdate,
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = snapshot(await controller.get_label(session, print_label_id))
    updated = await controller.update_label(session, print_label_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type=ENTITY,
        entity_id=print_label_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@router.get(
    "/{print_label_id}/versions",
    response_model=Page[PrintLabelVersionRead],
    responses=error_responses(404),
)
async def list_print_label_versions(
    _user: CanView,
    print_label_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    version_status: Annotated[VersionStatus | None, Depends(version_status_param)],
) -> Page[PrintLabelVersionRead]:
    """`?status=` filtra por estado (p. ej. solo `published`)."""
    return await controller.list_versions(
        session, print_label_id, pagination, version_status
    )


@router.post(
    "/{print_label_id}/versions",
    response_model=PrintLabelVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_print_label_version(
    print_label_id: UUID,
    data: PrintLabelVersionCreate,
    user: CanCreateVersion,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    """Nuevo draft: clona la ultima version (publicada o retirada), o crea
    la version 1 si la etiqueta todavia no tiene ninguna."""
    created = await controller.create_version(session, print_label_id, data)
    await record_audit(
        CREATE_VERSION,
        user,
        entity_type=VERSION_ENTITY,
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@router.patch(
    "/{print_label_id}/versions/{version_id}",
    response_model=PrintLabelVersionRead,
    responses=error_responses(404, 409, 422),
)
async def update_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    data: PrintLabelVersionUpdate,
    user: CanEditVersion,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    """Solo aplica si la version esta en `draft`."""
    before = snapshot(await controller.get_version(session, print_label_id, version_id))
    updated = await controller.update_version(session, print_label_id, version_id, data)
    await record_audit(
        EDIT_VERSION,
        user,
        entity_type=VERSION_ENTITY,
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


@router.post(
    "/{print_label_id}/versions/{version_id}/publish",
    response_model=PrintLabelVersionRead,
    responses=error_responses(404, 422),
)
async def publish_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    user: CanPublishVersion,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    before = snapshot(await controller.get_version(session, print_label_id, version_id))
    updated = await controller.publish_version(session, print_label_id, version_id)
    await record_audit(
        PUBLISH_VERSION,
        user,
        entity_type=VERSION_ENTITY,
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


@router.post(
    "/{print_label_id}/versions/{version_id}/retire",
    response_model=PrintLabelVersionRead,
    responses=RETIRE_VERSION_RESPONSES,
)
async def retire_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    user: CanRetireVersion,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    before = snapshot(await controller.get_version(session, print_label_id, version_id))
    updated = await controller.retire_version(session, print_label_id, version_id)
    await record_audit(
        RETIRE_VERSION,
        user,
        entity_type=VERSION_ENTITY,
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


@versions_router.get(
    "/{version_id}",
    response_model=PrintLabelVersionWithOwnerRead,
    responses=error_responses(404),
)
async def get_print_label_version(
    _user: CanView,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionWithOwnerRead:
    """Una version por su id, con su etiqueta duena en `owner`."""
    return await controller.get_version_with_owner(session, version_id)
