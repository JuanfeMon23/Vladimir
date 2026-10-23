"""Casos de uso / logica de negocio del modulo `consent_documents`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`. Las reglas de
ciclo de vida (`draft` -> `published` -> `retired`) las aplica
`VersioningService` (ver `app.core.versioning`), instanciado una sola vez
para este modulo.
"""

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import runtime_settings
from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError, ConflictError, NotFoundError
from app.core.repository import create_entity, get_or_404, update_entity
from app.core.schemas import Page
from app.core.versioning import VersioningService, VersionNotFoundError
from app.modules.consent_documents import repository
from app.modules.consent_documents.files import validate_pdf_base64
from app.modules.consent_documents.models import ConsentDocument, ConsentDocumentVersion
from app.modules.consent_documents.schemas import (
    DATA_TREATMENT_TYPE,
    ConsentDocumentCreate,
    ConsentDocumentFileRead,
    ConsentDocumentRead,
    ConsentDocumentUpdate,
    ConsentDocumentVersionRead,
    ConsentDocumentVersionWithOwnerRead,
    ConsentDocumentVersionWrite,
    DataTreatmentConsentRead,
)

# Indice unico parcial de la BD: a lo sumo un consentimiento general activo.
GENERAL_UNIQUE_INDEX = "uq_consent_documents_one_active_data_treatment"

versioning = VersioningService(
    ConsentDocumentVersion,
    "consent_document_id",
    parent_model=ConsentDocument,
    parent_noun="documento",
    read_schema=ConsentDocumentVersionRead,
    owner_read_schema=ConsentDocumentVersionWithOwnerRead,
    required_fields=("content", "signer"),
    # Publicar exige archivo; `file_sha256` indica su presencia sin cargar el
    # `file_base64` diferido. Se reporta como `file_base64` (el campo del body).
    publish_required={"file_base64": "file_sha256"},
)

# Ciclo de versiones (rutas `/consent-documents/{id}/versions...`): lo
# resuelve el servicio generico, este modulo solo declara lo especifico arriba.
list_versions = versioning.list_versions
get_version_with_owner = versioning.read_with_owner
get_version = versioning.read_version
publish_version = versioning.publish_version
retire_version = versioning.retire_version


async def _max_file_mib() -> int:
    return await runtime_settings.get("files.consent_max_mib")


def _with_file(data: BaseModel, max_mib: int) -> BaseModel:
    """Si el body trae `file_base64`, lo valida y devuelve el body a escribir
    con `file_sha256`/`file_size_bytes`/`file_content_type` calculados (nunca
    del cliente); `null` explicito quita el archivo (los 4 campos a `None`).
    Sin `file_base64` en el body, no se toca el archivo. `max_mib` es el ajuste
    `files.consent_max_mib` (leido por peticion).
    """
    changes = data.model_dump(exclude_unset=True)
    if "file_base64" not in changes:
        return ConsentDocumentVersionWrite(**changes)
    if changes["file_base64"] is None:
        derived = {
            "file_content_type": None,
            "file_sha256": None,
            "file_size_bytes": None,
        }
    else:
        pdf = validate_pdf_base64(changes["file_base64"], max_mib)
        derived = {
            "file_content_type": pdf.content_type,
            "file_sha256": pdf.sha256,
            "file_size_bytes": pdf.size_bytes,
        }
    return ConsentDocumentVersionWrite(**changes, **derived)


async def create_version(
    session: AsyncSession, consent_document_id: UUID, data: BaseModel
) -> ConsentDocumentVersionRead:
    return await versioning.create_version(
        session, consent_document_id, _with_file(data, await _max_file_mib())
    )


async def update_version(
    session: AsyncSession,
    consent_document_id: UUID,
    version_id: UUID,
    data: BaseModel,
) -> ConsentDocumentVersionRead:
    return await versioning.update_version(
        session,
        consent_document_id,
        version_id,
        _with_file(data, await _max_file_mib()),
    )


async def _load_file(
    session: AsyncSession, version: ConsentDocumentVersion
) -> ConsentDocumentFileRead:
    """Archivo de una version que se sabe con archivo (carga el diferido)."""
    await session.refresh(version, attribute_names=["file_base64"])
    return ConsentDocumentFileRead(
        content_type=version.file_content_type,  # type: ignore[arg-type]
        sha256=version.file_sha256,  # type: ignore[arg-type]
        size_bytes=version.file_size_bytes,  # type: ignore[arg-type]
        base64=version.file_base64,  # type: ignore[arg-type]
    )


async def get_version_file(
    session: AsyncSession, version_id: UUID
) -> ConsentDocumentFileRead:
    version = await session.get(ConsentDocumentVersion, version_id)
    if version is None:
        raise VersionNotFoundError("una versión de documento", version_id)
    if version.file_sha256 is None:
        raise NotFoundError(
            message=f"La versión '{version_id}' no tiene archivo.",
            details={"id": str(version_id)},
        )
    return await _load_file(session, version)


async def get_current_data_treatment(
    session: AsyncSession,
) -> DataTreatmentConsentRead:
    """Consentimiento general activo + su version publicada mas reciente +
    archivo (base64 incluido): lo que la app de firmas necesita."""
    document = await repository.get_active_general(session)
    if document is None:
        raise NotFoundError(
            message="No hay un documento activo de tratamiento de datos personales."
        )
    version = await repository.get_latest_published_version(session, document.id)
    if version is None:
        raise NotFoundError(
            message=(
                "El documento de tratamiento de datos personales "
                f"«{document.code}» no tiene una versión publicada."
            ),
            details={"id": str(document.id), "code": document.code},
        )
    return DataTreatmentConsentRead(
        document=ConsentDocumentRead.model_validate(document),
        version=ConsentDocumentVersionRead.model_validate(version),
        file=await _load_file(session, version) if version.file_sha256 else None,
    )


def _general_conflict(existing: ConsentDocument) -> ConflictError:
    return ConflictError(
        message=(
            "Ya existe un documento activo de tratamiento de datos personales "
            f"({existing.code}). Desactívalo antes de activar otro."
        ),
        details={"code": existing.code, "id": str(existing.id)},
    )


async def _ensure_single_general(
    session: AsyncSession, *, exclude_id: UUID | None = None
) -> None:
    """409 si ya hay OTRO consentimiento general activo."""
    existing = await repository.get_active_general(session, exclude_id=exclude_id)
    if existing is not None:
        raise _general_conflict(existing)


async def _translate_general_integrity_error(
    session: AsyncSession, error: IntegrityError, exclude_id: UUID | None
) -> Exception:
    """Red de seguridad (carrera): el indice unico de la BD -> el mismo 409.
    Cualquier otro `IntegrityError` se devuelve tal cual."""
    await session.rollback()
    if GENERAL_UNIQUE_INDEX not in str(error.orig):
        return error
    existing = await repository.get_active_general(session, exclude_id=exclude_id)
    return error if existing is None else _general_conflict(existing)


async def list_documents(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[ConsentDocumentRead]:
    documents, total = await repository.list_documents(
        session, pagination, active_filter, search
    )
    return Page[ConsentDocumentRead](
        items=[ConsentDocumentRead.model_validate(doc) for doc in documents],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_document(
    session: AsyncSession, data: ConsentDocumentCreate
) -> ConsentDocumentRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un documento", data.code)
    if data.document_type == DATA_TREATMENT_TYPE and data.is_active:
        await _ensure_single_general(session)
    try:
        document = await create_entity(session, ConsentDocument, data)
    except IntegrityError as error:
        raise await _translate_general_integrity_error(session, error, None) from error
    return ConsentDocumentRead.model_validate(document)


async def get_document(
    session: AsyncSession, consent_document_id: UUID
) -> ConsentDocumentRead:
    document = await get_or_404(
        session, ConsentDocument, consent_document_id, "un documento"
    )
    return ConsentDocumentRead.model_validate(document)


async def update_document(
    session: AsyncSession, consent_document_id: UUID, data: ConsentDocumentUpdate
) -> ConsentDocumentRead:
    document = await get_or_404(
        session, ConsentDocument, consent_document_id, "un documento"
    )

    new_code = data.code
    if new_code is not None and new_code != document.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un documento", new_code)

    changes = data.model_dump(exclude_unset=True)
    final_type = changes.get("document_type", document.document_type)
    final_active = changes.get("is_active", document.is_active)
    if final_type == DATA_TREATMENT_TYPE and final_active:
        await _ensure_single_general(session, exclude_id=document.id)

    document_id = document.id
    try:
        document = await update_entity(session, document, data)
    except IntegrityError as error:
        raise await _translate_general_integrity_error(
            session, error, document_id
        ) from error
    return ConsentDocumentRead.model_validate(document)
