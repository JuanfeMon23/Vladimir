"""Rutas HTTP del modulo `consent_documents`. Delgadas: solo traducen HTTP <-> controller."""

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
from app.modules.consent_documents import controller
from app.modules.consent_documents.schemas import (
    ConsentDocumentCreate,
    ConsentDocumentFileRead,
    ConsentDocumentRead,
    ConsentDocumentUpdate,
    ConsentDocumentVersionCreate,
    ConsentDocumentVersionRead,
    ConsentDocumentVersionUpdate,
    ConsentDocumentVersionWithOwnerRead,
    DataTreatmentConsentRead,
)

router = APIRouter(tags=["consent_documents"])
versions_router = APIRouter(tags=["consent_documents"])


@router.get("", response_model=Page[ConsentDocumentRead])
async def list_consent_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    active_filter: Annotated[ActiveOnlyFilter, Depends(active_only_filter)],
    search: Annotated[SearchFilter, Depends(search_filter)],
) -> Page[ConsentDocumentRead]:
    return await controller.list_documents(session, pagination, active_filter, search)


@router.post(
    "",
    response_model=ConsentDocumentRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_consent_document(
    data: ConsentDocumentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentRead:
    return await controller.create_document(session, data)


@router.get(
    "/data-treatment/current",
    response_model=DataTreatmentConsentRead,
    responses=error_responses(
        404,
        descriptions={
            404: "No hay documento activo de tratamiento de datos personales, "
            "o no tiene versión publicada."
        },
    ),
)
async def get_current_data_treatment_consent(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DataTreatmentConsentRead:
    """Consentimiento general de tratamiento de datos personales vigente: el
    documento activo de tipo `tratamiento_datos`, su versión publicada más
    reciente y el archivo PDF en base64 (`file`). Es el que la aplicación de
    firmas muestra y firma primero, para todo paciente."""
    return await controller.get_current_data_treatment(session)


@router.get(
    "/{consent_document_id}",
    response_model=ConsentDocumentRead,
    responses=error_responses(404),
)
async def get_consent_document(
    consent_document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentRead:
    return await controller.get_document(session, consent_document_id)


@router.patch(
    "/{consent_document_id}",
    response_model=ConsentDocumentRead,
    responses=error_responses(404, 409, 422),
)
async def update_consent_document(
    consent_document_id: UUID,
    data: ConsentDocumentUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentRead:
    return await controller.update_document(session, consent_document_id, data)


@router.get(
    "/{consent_document_id}/versions",
    response_model=Page[ConsentDocumentVersionRead],
    responses=error_responses(404),
)
async def list_consent_document_versions(
    consent_document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    version_status: Annotated[VersionStatus | None, Depends(version_status_param)],
) -> Page[ConsentDocumentVersionRead]:
    """`?status=` filtra por estado (p. ej. solo `published`)."""
    return await controller.list_versions(
        session, consent_document_id, pagination, version_status
    )


@router.post(
    "/{consent_document_id}/versions",
    response_model=ConsentDocumentVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_consent_document_version(
    consent_document_id: UUID,
    data: ConsentDocumentVersionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentVersionRead:
    """Nuevo draft: clona la ultima version (publicada o retirada), o crea
    la version 1 si el documento todavia no tiene ninguna. `file_base64`
    (opcional) sube el PDF; al clonar se hereda el de la versión anterior."""
    return await controller.create_version(session, consent_document_id, data)


@router.patch(
    "/{consent_document_id}/versions/{version_id}",
    response_model=ConsentDocumentVersionRead,
    responses=error_responses(404, 409, 422),
)
async def update_consent_document_version(
    consent_document_id: UUID,
    version_id: UUID,
    data: ConsentDocumentVersionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentVersionRead:
    """Solo aplica si la version esta en `draft`. `file_base64` reemplaza el
    PDF; `null` lo quita; omitirlo no lo toca."""
    return await controller.update_version(
        session, consent_document_id, version_id, data
    )


@router.post(
    "/{consent_document_id}/versions/{version_id}/publish",
    response_model=ConsentDocumentVersionRead,
    responses=error_responses(
        404,
        422,
        descriptions={
            422: "Solo se publica un borrador y con archivo "
            '(`details.missing_fields = ["file_base64"]` si no lo tiene).'
        },
    ),
)
async def publish_consent_document_version(
    consent_document_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentVersionRead:
    return await controller.publish_version(session, consent_document_id, version_id)


@router.post(
    "/{consent_document_id}/versions/{version_id}/retire",
    response_model=ConsentDocumentVersionRead,
    responses=RETIRE_VERSION_RESPONSES,
)
async def retire_consent_document_version(
    consent_document_id: UUID,
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentVersionRead:
    return await controller.retire_version(session, consent_document_id, version_id)


@versions_router.get(
    "/{version_id}",
    response_model=ConsentDocumentVersionWithOwnerRead,
    responses=error_responses(404),
)
async def get_consent_document_version(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentVersionWithOwnerRead:
    """Una version por su id, con su documento dueno en `owner`."""
    return await controller.get_version_with_owner(session, version_id)


@versions_router.get(
    "/{version_id}/file",
    response_model=ConsentDocumentFileRead,
    responses=error_responses(
        404,
        descriptions={404: "La versión no existe o no tiene archivo."},
    ),
)
async def get_consent_document_version_file(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConsentDocumentFileRead:
    """Archivo PDF de una versión, en base64, con su tipo, SHA-256 y tamaño."""
    return await controller.get_version_file(session, version_id)
