"""Rutas HTTP del modulo `print_labels`. Delgadas: solo traducen HTTP <-> controller."""

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
    version_status_param,
)
from app.core.schemas import Page, error_responses
from app.core.versioning import RETIRE_VERSION_RESPONSES, VersionStatus
from app.modules.print_labels import controller
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


@router.get("", response_model=Page[PrintLabelRead])
async def list_print_labels(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelRead:
    return await controller.create_label(session, data)


@router.get(
    "/{print_label_id}", response_model=PrintLabelRead, responses=error_responses(404)
)
async def get_print_label(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelRead:
    return await controller.update_label(session, print_label_id, data)


@router.get(
    "/{print_label_id}/versions",
    response_model=Page[PrintLabelVersionRead],
    responses=error_responses(404),
)
async def list_print_label_versions(
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    """Nuevo draft: clona la ultima version (publicada o retirada), o crea
    la version 1 si la etiqueta todavia no tiene ninguna."""
    return await controller.create_version(session, print_label_id, data)


@router.patch(
    "/{print_label_id}/versions/{version_id}",
    response_model=PrintLabelVersionRead,
    responses=error_responses(404, 409, 422),
)
async def update_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    data: PrintLabelVersionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    """Solo aplica si la version esta en `draft`."""
    return await controller.update_version(session, print_label_id, version_id, data)


@router.post(
    "/{print_label_id}/versions/{version_id}/publish",
    response_model=PrintLabelVersionRead,
    responses=error_responses(404, 422),
)
async def publish_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    return await controller.publish_version(session, print_label_id, version_id)


@router.post(
    "/{print_label_id}/versions/{version_id}/retire",
    response_model=PrintLabelVersionRead,
    responses=RETIRE_VERSION_RESPONSES,
)
async def retire_print_label_version(
    print_label_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionRead:
    return await controller.retire_version(session, print_label_id, version_id)


@versions_router.get(
    "/{version_id}",
    response_model=PrintLabelVersionWithOwnerRead,
    responses=error_responses(404),
)
async def get_print_label_version(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrintLabelVersionWithOwnerRead:
    """Una version por su id, con su etiqueta duena en `owner`."""
    return await controller.get_version_with_owner(session, version_id)
