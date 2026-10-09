"""Tests del controller de `preconditions` (sin HTTP)."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError
from app.modules.preconditions import controller
from app.modules.preconditions.exceptions import (
    PreconditionHierarchyError,
)
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionUpdate,
)
from app.modules.preconditions.tests.conftest import unique_code


async def test_create_precondition(
    session: AsyncSession, precondition_payload: dict
) -> None:
    created = await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )

    assert created.code == precondition_payload["code"]
    assert created.kind == "precondition"
    assert created.parent_id is None
    assert created.items == []


async def test_create_precondition_duplicate_code_raises_conflict(
    session: AsyncSession, precondition_payload: dict
) -> None:
    await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )

    with pytest.raises(
        CodeConflictError, match="Ya existe una precondición con el código"
    ):
        await controller.create_precondition(
            session, PreconditionCreate(**precondition_payload)
        )


async def test_create_item(
    session: AsyncSession, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    root = await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )

    item = await controller.create_item(
        session, root.id, PreconditionItemCreate(**precondition_item_payload)
    )

    assert item.kind == "condition"
    assert item.parent_id == root.id


async def test_create_item_under_item_raises_hierarchy_error(
    session: AsyncSession, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    root = await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )
    item = await controller.create_item(
        session, root.id, PreconditionItemCreate(**precondition_item_payload)
    )

    grandchild_payload = {**precondition_item_payload, "code": unique_code()}
    with pytest.raises(PreconditionHierarchyError):
        await controller.create_item(
            session, item.id, PreconditionItemCreate(**grandchild_payload)
        )


async def test_create_item_under_missing_parent_raises_not_found(
    session: AsyncSession, precondition_item_payload: dict
) -> None:
    with pytest.raises(NotFoundError, match="No existe una precondicion con id"):
        await controller.create_item(
            session, uuid4(), PreconditionItemCreate(**precondition_item_payload)
        )


async def test_get_precondition_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe una precondicion con id"):
        await controller.get_precondition(session, uuid4())


async def test_list_preconditions_includes_nested_items(
    session: AsyncSession, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    root = await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )
    item = await controller.create_item(
        session, root.id, PreconditionItemCreate(**precondition_item_payload)
    )

    page = await controller.list_preconditions(
        session,
        PaginationParams(page=1, page_size=50),
        ActiveOnlyFilter(active=None),
    )

    found = next((p for p in page.items if p.id == root.id), None)
    assert found is not None
    assert found.items is not None
    assert {i.id for i in found.items} == {item.id}


async def test_update_precondition(
    session: AsyncSession, precondition_payload: dict
) -> None:
    created = await controller.create_precondition(
        session, PreconditionCreate(**precondition_payload)
    )

    updated = await controller.update_precondition(
        session, created.id, PreconditionUpdate(name="Ayuno de 12 horas")
    )

    assert updated.name == "Ayuno de 12 horas"
    assert updated.code == precondition_payload["code"]


async def test_create_item_under_inactive_precondition_raises_inactive_reference(
    session: AsyncSession, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    parent = await controller.create_precondition(
        session, PreconditionCreate(**{**precondition_payload, "is_active": False})
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_item(
            session, parent.id, PreconditionItemCreate(**precondition_item_payload)
        )
    assert exc_info.value.details == {"parent_id": str(parent.id)}
