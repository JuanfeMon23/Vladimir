"""Tests de `core/categories.py`: referencias a catalogos de categoria."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.categories import ensure_category, get_category
from app.core.exceptions import InvalidReferenceError
from app.modules.samples.models import SpecimenType


async def _ensure(session: AsyncSession, code: str | None, **extra: object):
    return await ensure_category(
        session,
        SpecimenType,
        code,
        subject="el espécimen",
        field="specimen",
        **extra,  # type: ignore[arg-type]
    )


async def test_devuelve_la_fila_si_existe_y_esta_activa(session: AsyncSession) -> None:
    row = await _ensure(session, "suero")

    assert row is not None
    assert row.code == "suero"


async def test_codigo_inexistente_es_invalid_reference(session: AsyncSession) -> None:
    with pytest.raises(InvalidReferenceError) as error:
        await _ensure(session, "no-existe")

    assert error.value.code == "invalid_reference"
    assert error.value.details == {"specimen": "no-existe"}


async def test_codigo_inactivo_es_inactive_reference(session: AsyncSession) -> None:
    row = await get_category(session, SpecimenType, "orina")
    assert row is not None
    row.is_active = False
    await session.flush()

    with pytest.raises(InactiveReferenceError) as error:
        await _ensure(session, "orina")

    assert error.value.code == "inactive_reference"
    assert "orina" in error.value.message


async def test_none_no_se_valida(session: AsyncSession) -> None:
    assert await _ensure(session, None) is None


async def test_valor_que_la_fila_ya_tenia_no_se_revalida(
    session: AsyncSession,
) -> None:
    row = await get_category(session, SpecimenType, "orina")
    assert row is not None
    row.is_active = False
    await session.flush()

    assert await _ensure(session, "orina", current="orina") is None
