"""Tests del controller de `samples` (sin HTTP)."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError
from app.modules.samples import controller
from app.modules.samples.schemas import (
    SampleCreate,
    SampleTypeCreate,
    SampleTypeUpdate,
    SampleUpdate,
)
from app.modules.samples.tests.conftest import unique_code


async def test_create_sample(session: AsyncSession, sample_payload: dict) -> None:
    created = await controller.create_sample(session, SampleCreate(**sample_payload))

    assert created.code == sample_payload["code"]
    assert created.types == []


async def test_create_sample_duplicate_code_raises_conflict(
    session: AsyncSession, sample_payload: dict
) -> None:
    await controller.create_sample(session, SampleCreate(**sample_payload))

    with pytest.raises(CodeConflictError, match="Ya existe una muestra con el código"):
        await controller.create_sample(session, SampleCreate(**sample_payload))


async def test_create_sample_type(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(session, SampleCreate(**sample_payload))

    sample_type = await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**sample_type_payload)
    )

    assert sample_type.sample_id == sample.id
    assert sample_type.specimen == "suero"


async def test_create_sample_type_under_missing_sample_raises_not_found(
    session: AsyncSession, sample_type_payload: dict
) -> None:
    with pytest.raises(NotFoundError, match="No existe una muestra con id"):
        await controller.create_sample_type(
            session, uuid4(), SampleTypeCreate(**sample_type_payload)
        )


async def test_create_sample_type_duplicate_code_raises_conflict(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(session, SampleCreate(**sample_payload))
    await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**sample_type_payload)
    )

    with pytest.raises(
        CodeConflictError, match="Ya existe un tipo de muestra con el código"
    ):
        await controller.create_sample_type(
            session, sample.id, SampleTypeCreate(**sample_type_payload)
        )


async def test_get_sample_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe una muestra con id"):
        await controller.get_sample(session, uuid4())


async def test_list_samples_includes_nested_types(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(session, SampleCreate(**sample_payload))
    sample_type = await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**sample_type_payload)
    )

    page = await controller.list_samples(
        session,
        PaginationParams(page=1, page_size=50),
        ActiveOnlyFilter(active=None),
    )

    found = next((s for s in page.items if s.id == sample.id), None)
    assert found is not None
    assert {t.id for t in found.types} == {sample_type.id}


async def test_update_sample(session: AsyncSession, sample_payload: dict) -> None:
    created = await controller.create_sample(session, SampleCreate(**sample_payload))

    updated = await controller.update_sample(
        session, created.id, SampleUpdate(name="Sangre venosa")
    )

    assert updated.name == "Sangre venosa"
    assert updated.code == sample_payload["code"]


async def test_update_sample_type(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(session, SampleCreate(**sample_payload))
    sample_type = await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**sample_type_payload)
    )

    updated = await controller.update_sample_type(
        session, sample_type.id, SampleTypeUpdate(name="Tubo tapa lila")
    )

    assert updated.name == "Tubo tapa lila"
    assert updated.sample_id == sample.id


async def test_update_sample_type_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe un tipo de muestra con id"):
        await controller.update_sample_type(
            session, uuid4(), SampleTypeUpdate(name="x")
        )


async def test_list_sample_types_under_missing_sample_raises_not_found(
    session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError, match="No existe una muestra con id"):
        await controller.list_sample_types(
            session,
            uuid4(),
            PaginationParams(page=1, page_size=50),
            ActiveOnlyFilter(active=None),
        )


async def test_update_sample_type_duplicate_code_raises_conflict(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(session, SampleCreate(**sample_payload))
    first = await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**sample_type_payload)
    )
    other_payload = {**sample_type_payload, "code": unique_code()}
    second = await controller.create_sample_type(
        session, sample.id, SampleTypeCreate(**other_payload)
    )

    with pytest.raises(
        CodeConflictError, match="Ya existe un tipo de muestra con el código"
    ):
        await controller.update_sample_type(
            session, second.id, SampleTypeUpdate(code=first.code)
        )


async def test_create_type_under_inactive_sample_raises_inactive_reference(
    session: AsyncSession, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample = await controller.create_sample(
        session, SampleCreate(**{**sample_payload, "is_active": False})
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_sample_type(
            session, sample.id, SampleTypeCreate(**sample_type_payload)
        )
    assert exc_info.value.details == {"sample_id": str(sample.id)}
