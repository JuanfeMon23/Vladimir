"""Tests del controller de `lab_areas` (sin HTTP)."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.db.activity import ActivityEvent
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError
from app.modules.lab_areas import controller
from app.modules.lab_areas.exceptions import (
    StaffNotEligibleForManagerError,
)
from app.modules.lab_areas.schemas import (
    LabAreaCreate,
    LabAreaUpdate,
    ManagerAssignmentCreate,
)
from app.modules.lab_areas.tests.conftest import unique_code
from app.modules.staff.models import Staff


async def test_create_lab_area(session: AsyncSession, lab_area_payload: dict) -> None:
    created = await controller.create_lab_area(
        session, LabAreaCreate(**lab_area_payload)
    )

    assert created.code == lab_area_payload["code"]
    assert created.is_active is True
    assert created.current_manager is None


async def test_create_lab_area_duplicate_code_raises_conflict(
    session: AsyncSession, lab_area_payload: dict
) -> None:
    await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    with pytest.raises(CodeConflictError, match="Ya existe un área con el código"):
        await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))


async def test_get_lab_area_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe un area con id"):
        await controller.get_lab_area(session, uuid4())


async def test_list_lab_areas_filters_by_active(
    session: AsyncSession, lab_area_payload: dict
) -> None:
    active = await controller.create_lab_area(
        session, LabAreaCreate(**lab_area_payload)
    )

    inactive_payload = {**lab_area_payload, "code": unique_code(), "is_active": False}
    inactive = await controller.create_lab_area(
        session, LabAreaCreate(**inactive_payload)
    )

    page = await controller.list_lab_areas(
        session,
        PaginationParams(page=1, page_size=20),
        ActiveOnlyFilter(active=True),
    )

    ids = {item.id for item in page.items}
    assert active.id in ids
    assert inactive.id not in ids


async def test_update_lab_area(session: AsyncSession, lab_area_payload: dict) -> None:
    created = await controller.create_lab_area(
        session, LabAreaCreate(**lab_area_payload)
    )

    updated = await controller.update_lab_area(
        session, created.id, LabAreaUpdate(description="Nueva descripcion")
    )

    assert updated.description == "Nueva descripcion"
    assert updated.name == lab_area_payload["name"]


async def test_assign_manager_sets_current_manager(
    session: AsyncSession, lab_area_payload: dict, active_staff: Staff
) -> None:
    area = await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    assignment = await controller.assign_manager(
        session, area.id, ManagerAssignmentCreate(staff_id=active_staff.id)
    )

    assert assignment.staff_id == active_staff.id
    assert assignment.end_at is None

    refreshed = await controller.get_lab_area(session, area.id)
    assert refreshed.current_manager is not None
    assert refreshed.current_manager.staff_id == active_staff.id


async def test_assign_manager_rejects_inactive_staff(
    session: AsyncSession, lab_area_payload: dict, inactive_staff: Staff
) -> None:
    area = await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    with pytest.raises(StaffNotEligibleForManagerError):
        await controller.assign_manager(
            session, area.id, ManagerAssignmentCreate(staff_id=inactive_staff.id)
        )


async def test_assign_manager_rejects_unknown_staff(
    session: AsyncSession, lab_area_payload: dict
) -> None:
    area = await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    with pytest.raises(StaffNotEligibleForManagerError):
        await controller.assign_manager(
            session, area.id, ManagerAssignmentCreate(staff_id=uuid4())
        )


async def test_assign_manager_unknown_area_raises_not_found(
    session: AsyncSession, active_staff: Staff
) -> None:
    with pytest.raises(NotFoundError, match="No existe un area con id"):
        await controller.assign_manager(
            session, uuid4(), ManagerAssignmentCreate(staff_id=active_staff.id)
        )


async def test_change_manager_closes_previous_and_opens_new(
    session: AsyncSession,
    lab_area_payload: dict,
    active_staff: Staff,
    inactive_staff: Staff,
) -> None:
    # Reactivamos el segundo staff para usarlo como nuevo encargado.
    inactive_staff.is_active = True
    await session.commit()

    area = await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    first = await controller.assign_manager(
        session, area.id, ManagerAssignmentCreate(staff_id=active_staff.id)
    )
    second = await controller.assign_manager(
        session, area.id, ManagerAssignmentCreate(staff_id=inactive_staff.id)
    )

    history = await controller.get_manager_history(session, area.id)
    by_id = {item.id: item for item in history}

    assert by_id[first.id].end_at is not None
    assert by_id[second.id].end_at is None

    refreshed = await controller.get_lab_area(session, area.id)
    assert refreshed.current_manager is not None
    assert refreshed.current_manager.staff_id == inactive_staff.id


async def test_manager_history_unknown_area_raises_not_found(
    session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError, match="No existe un area con id"):
        await controller.get_manager_history(session, uuid4())


async def test_assign_manager_rejects_inactive_area(
    session: AsyncSession, lab_area_payload: dict, active_staff: Staff
) -> None:
    area = await controller.create_lab_area(
        session, LabAreaCreate(**{**lab_area_payload, "is_active": False})
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.assign_manager(
            session, area.id, ManagerAssignmentCreate(staff_id=active_staff.id)
        )
    assert exc_info.value.details == {"area_id": str(area.id)}


async def test_deactivate_area_with_reason_is_logged(
    session: AsyncSession, lab_area_payload: dict
) -> None:
    area = await controller.create_lab_area(session, LabAreaCreate(**lab_area_payload))

    updated = await controller.update_lab_area(
        session,
        area.id,
        LabAreaUpdate(is_active=False, activity_reason="Remodelacion"),
    )

    assert updated.is_active is False
    reasons = (
        (
            await session.execute(
                select(ActivityEvent.reason).where(
                    ActivityEvent.entity_id == area.id,
                    ActivityEvent.action == "deactivated",
                )
            )
        )
        .scalars()
        .all()
    )
    assert reasons == ["Remodelacion"]
