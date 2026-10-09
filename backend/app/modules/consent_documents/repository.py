"""Acceso a datos del modulo `consent_documents`. Unico archivo que arma consultas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.consent_documents.models import (
    ConsentDocument,
    ConsentDocumentVersion,
)
from app.modules.consent_documents.schemas import DATA_TREATMENT_TYPE


async def get_by_code(session: AsyncSession, code: str) -> ConsentDocument | None:
    stmt = select(ConsentDocument).where(ConsentDocument.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[ConsentDocument], int]:
    stmt = active_filter.apply(select(ConsentDocument), ConsentDocument.is_active)
    stmt = search.apply(stmt, ConsentDocument.code, ConsentDocument.name)
    return await paginate(session, stmt, pagination, ConsentDocument.name)


async def get_active_general(
    session: AsyncSession, *, exclude_id: UUID | None = None
) -> ConsentDocument | None:
    """El consentimiento general (`tratamiento_datos`) ACTIVO, salvo `exclude_id`."""
    stmt = select(ConsentDocument).where(
        ConsentDocument.document_type == DATA_TREATMENT_TYPE,
        ConsentDocument.is_active.is_(True),
    )
    if exclude_id is not None:
        stmt = stmt.where(ConsentDocument.id != exclude_id)
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def get_latest_published_version(
    session: AsyncSession, consent_document_id: UUID
) -> ConsentDocumentVersion | None:
    """La version publicada mas reciente (mayor `version_number`) del documento."""
    stmt = (
        select(ConsentDocumentVersion)
        .where(
            ConsentDocumentVersion.consent_document_id == consent_document_id,
            ConsentDocumentVersion.status == "published",
        )
        .order_by(ConsentDocumentVersion.version_number.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
