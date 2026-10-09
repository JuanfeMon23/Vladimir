"""Casos de uso / logica de negocio del modulo `staff`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`, solo excepciones
de `app.core.exceptions` que el nucleo traduce a HTTP.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import DuplicateValueError
from app.core.repository import create_entity, get_or_404, update_entity
from app.core.schemas import Page
from app.modules.staff import repository
from app.modules.staff.models import Staff
from app.modules.staff.schemas import StaffCreate, StaffRead, StaffUpdate


async def list_staff(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[StaffRead]:
    items, total = await repository.list_staff(
        session, pagination, active_filter, search
    )
    return Page[StaffRead](
        items=[StaffRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_staff(session: AsyncSession, data: StaffCreate) -> StaffRead:
    existing = await repository.get_by_document_number(session, data.document_number)
    if existing is not None:
        raise DuplicateValueError(
            entity="personal",
            field="document_number",
            field_label="el número de documento",
            value=data.document_number,
        )
    staff = await create_entity(session, Staff, data)
    return StaffRead.model_validate(staff)


async def get_staff(session: AsyncSession, staff_id: UUID) -> StaffRead:
    staff = await get_or_404(session, Staff, staff_id, "personal")
    return StaffRead.model_validate(staff)


async def update_staff(
    session: AsyncSession, staff_id: UUID, data: StaffUpdate
) -> StaffRead:
    staff = await get_or_404(session, Staff, staff_id, "personal")

    new_document_number = data.document_number
    if new_document_number is not None and new_document_number != staff.document_number:
        existing = await repository.get_by_document_number(session, new_document_number)
        if existing is not None:
            raise DuplicateValueError(
                entity="personal",
                field="document_number",
                field_label="el número de documento",
                value=new_document_number,
            )

    staff = await update_entity(session, staff, data)
    return StaffRead.model_validate(staff)
