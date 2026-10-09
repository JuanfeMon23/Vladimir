"""Tests del controller de `staff` (sin HTTP)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import DuplicateValueError, NotFoundError
from app.modules.staff import controller
from app.modules.staff.schemas import StaffCreate, StaffUpdate
from app.modules.staff.tests.conftest import unique_document_number


async def test_create_staff(session: AsyncSession, staff_payload: dict) -> None:
    created = await controller.create_staff(session, StaffCreate(**staff_payload))

    assert created.document_number == staff_payload["document_number"]
    assert created.is_active is True


async def test_create_staff_duplicate_document_number_raises_conflict(
    session: AsyncSession, staff_payload: dict
) -> None:
    await controller.create_staff(session, StaffCreate(**staff_payload))

    with pytest.raises(
        DuplicateValueError, match="Ya existe personal con el número de documento"
    ):
        await controller.create_staff(session, StaffCreate(**staff_payload))


async def test_get_staff_not_found_raises(session: AsyncSession) -> None:
    from uuid import uuid4

    with pytest.raises(NotFoundError, match="No existe personal con id"):
        await controller.get_staff(session, uuid4())


async def test_list_staff_filters_by_active(
    session: AsyncSession, staff_payload: dict
) -> None:
    active = await controller.create_staff(session, StaffCreate(**staff_payload))

    inactive_payload = {
        **staff_payload,
        "document_number": unique_document_number(),
        "is_active": False,
    }
    inactive = await controller.create_staff(session, StaffCreate(**inactive_payload))

    page = await controller.list_staff(
        session,
        PaginationParams(page=1, page_size=20),
        ActiveOnlyFilter(active=True),
    )

    ids = {item.id for item in page.items}
    assert active.id in ids
    assert inactive.id not in ids


async def test_update_staff(session: AsyncSession, staff_payload: dict) -> None:
    created = await controller.create_staff(session, StaffCreate(**staff_payload))

    updated = await controller.update_staff(
        session, created.id, StaffUpdate(job_title="Coordinadora")
    )

    assert updated.job_title == "Coordinadora"
    assert updated.first_name == staff_payload["first_name"]
