"""Acceso a datos del modulo `lab_areas`. Unico archivo que arma consultas.

Nota: las consultas de encargado hacen JOIN con `staff` directamente (el
modulo `staff` no expone una interfaz publica de consulta). "Personal activo
por id" ya no se arma aqui: es `core.activation.get_active_by_id`.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.lab_areas.exceptions import ManagerAssignmentConflictError
from app.modules.lab_areas.models import LabArea, LabAreaManagerAssignment
from app.modules.staff.models import Staff


async def get_by_code(session: AsyncSession, code: str) -> LabArea | None:
    stmt = select(LabArea).where(LabArea.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_lab_areas(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[LabArea], int]:
    stmt = active_filter.apply(select(LabArea), LabArea.is_active)
    stmt = search.apply(stmt, LabArea.code, LabArea.name)
    return await paginate(session, stmt, pagination, LabArea.name)


async def get_current_manager(
    session: AsyncSession, area_id: UUID
) -> tuple[LabAreaManagerAssignment, Staff] | None:
    stmt = (
        select(LabAreaManagerAssignment, Staff)
        .join(Staff, Staff.id == LabAreaManagerAssignment.staff_id)
        .where(
            LabAreaManagerAssignment.area_id == area_id,
            LabAreaManagerAssignment.end_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    return result.one_or_none()


async def get_current_managers_bulk(
    session: AsyncSession, area_ids: list[UUID]
) -> dict[UUID, tuple[LabAreaManagerAssignment, Staff]]:
    if not area_ids:
        return {}
    stmt = (
        select(LabAreaManagerAssignment, Staff)
        .join(Staff, Staff.id == LabAreaManagerAssignment.staff_id)
        .where(
            LabAreaManagerAssignment.area_id.in_(area_ids),
            LabAreaManagerAssignment.end_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    return {
        assignment.area_id: (assignment, staff) for assignment, staff in result.all()
    }


async def get_manager_history(
    session: AsyncSession, area_id: UUID
) -> list[tuple[LabAreaManagerAssignment, Staff]]:
    stmt = (
        select(LabAreaManagerAssignment, Staff)
        .join(Staff, Staff.id == LabAreaManagerAssignment.staff_id)
        .where(LabAreaManagerAssignment.area_id == area_id)
        .order_by(LabAreaManagerAssignment.start_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.all())


async def assign_manager(
    session: AsyncSession,
    area_id: UUID,
    staff_id: UUID,
    start_at: datetime | None,
    notes: str | None,
) -> LabAreaManagerAssignment:
    """Cierra la asignacion vigente (si existe) y abre una nueva, en una sola
    transaccion (ver AGENTS.md "Transacciones" y la nota de bóveda
    `Asignacion de encargado de area`).

    El indice unico parcial `(area_id) WHERE end_at IS NULL` es la red de
    seguridad ante condiciones de carrera entre dos requests concurrentes.
    """
    now = datetime.now(UTC)

    close_stmt = (
        select(LabAreaManagerAssignment)
        .where(
            LabAreaManagerAssignment.area_id == area_id,
            LabAreaManagerAssignment.end_at.is_(None),
        )
        .with_for_update()
    )
    current = (await session.execute(close_stmt)).scalar_one_or_none()
    if current is not None:
        current.end_at = now

    new_assignment = LabAreaManagerAssignment(
        area_id=area_id,
        staff_id=staff_id,
        start_at=start_at or now,
        notes=notes,
    )
    session.add(new_assignment)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ManagerAssignmentConflictError(str(area_id)) from exc

    await session.refresh(new_assignment)
    return new_assignment
