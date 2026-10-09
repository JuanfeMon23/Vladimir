"""Casos de uso / logica de negocio del modulo `lab_areas`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`, solo excepciones
de `app.modules.lab_areas.exceptions` que el nucleo traduce a HTTP.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active, get_active_by_id
from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError
from app.core.repository import create_entity, get_or_404, update_entity
from app.core.schemas import Page
from app.modules.lab_areas import repository
from app.modules.lab_areas.exceptions import (
    StaffNotEligibleForManagerError,
)
from app.modules.lab_areas.models import LabArea, LabAreaManagerAssignment
from app.modules.lab_areas.schemas import (
    LabAreaCreate,
    LabAreaRead,
    LabAreaUpdate,
    ManagerAssignmentCreate,
    ManagerAssignmentRead,
)
from app.modules.staff.models import Staff


def _staff_full_name(staff: Staff) -> str:
    return f"{staff.first_name} {staff.last_name}"


def _assignment_to_read(
    assignment: LabAreaManagerAssignment, staff: Staff
) -> ManagerAssignmentRead:
    return ManagerAssignmentRead(
        id=assignment.id,
        area_id=assignment.area_id,
        staff_id=assignment.staff_id,
        staff_name=_staff_full_name(staff),
        start_at=assignment.start_at,
        end_at=assignment.end_at,
        notes=assignment.notes,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


async def _area_to_read(session: AsyncSession, area: LabArea) -> LabAreaRead:
    current = await repository.get_current_manager(session, area.id)
    base = LabAreaRead.model_validate(area)
    if current is None:
        return base
    assignment, staff = current
    return base.model_copy(
        update={"current_manager": _assignment_to_read(assignment, staff)}
    )


async def list_lab_areas(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[LabAreaRead]:
    items, total = await repository.list_lab_areas(
        session, pagination, active_filter, search
    )

    managers = await repository.get_current_managers_bulk(
        session, [item.id for item in items]
    )

    reads = []
    for item in items:
        base = LabAreaRead.model_validate(item)
        current = managers.get(item.id)
        if current is not None:
            assignment, staff = current
            base = base.model_copy(
                update={"current_manager": _assignment_to_read(assignment, staff)}
            )
        reads.append(base)

    return Page[LabAreaRead](
        items=reads,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_lab_area(session: AsyncSession, data: LabAreaCreate) -> LabAreaRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un área", data.code)
    area = await create_entity(session, LabArea, data)
    return await _area_to_read(session, area)


async def get_lab_area(session: AsyncSession, area_id: UUID) -> LabAreaRead:
    area = await get_or_404(session, LabArea, area_id, "un area")
    return await _area_to_read(session, area)


async def update_lab_area(
    session: AsyncSession, area_id: UUID, data: LabAreaUpdate
) -> LabAreaRead:
    area = await get_or_404(session, LabArea, area_id, "un area")

    new_code = data.code
    if new_code is not None and new_code != area.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un área", new_code)

    area = await update_entity(session, area, data)
    return await _area_to_read(session, area)


async def assign_manager(
    session: AsyncSession, area_id: UUID, data: ManagerAssignmentCreate
) -> ManagerAssignmentRead:
    area = await get_or_404(session, LabArea, area_id, "un area")
    ensure_active(area, subject="el área", field="area_id", feminine=True)

    staff = await get_active_by_id(session, Staff, data.staff_id)
    if staff is None:
        raise StaffNotEligibleForManagerError(str(data.staff_id))

    assignment = await repository.assign_manager(
        session,
        area_id=area_id,
        staff_id=data.staff_id,
        start_at=data.start_at,
        notes=data.notes,
    )
    return _assignment_to_read(assignment, staff)


async def get_manager_history(
    session: AsyncSession, area_id: UUID
) -> list[ManagerAssignmentRead]:
    await get_or_404(session, LabArea, area_id, "un area")
    history = await repository.get_manager_history(session, area_id)
    return [_assignment_to_read(assignment, staff) for assignment, staff in history]
