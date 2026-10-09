"""Fixtures de test del modulo `lab_areas`: BD real local, aislada por test.

Cada test corre dentro de una transaccion externa que se revierte al final
(savepoint anidado para sobrevivir a los `commit()` del repository), asi no
hace falta mockear la BD ni limpiar datos a mano. Mismo patron que
`app/modules/staff/tests/conftest.py`.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.staff.models import Staff


def unique_code() -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"area-{uuid4().hex[:24]}"


def unique_document_number() -> str:
    return uuid4().hex[:32]


@pytest.fixture
def lab_area_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Microbiologia",
        "description": "Area de microbiologia clinica",
    }


@pytest_asyncio.fixture
async def active_staff(session: AsyncSession) -> Staff:
    staff = Staff(
        document_type="CC",
        document_number=unique_document_number(),
        first_name="Laura",
        last_name="Perez",
        is_active=True,
    )
    session.add(staff)
    await session.commit()
    await session.refresh(staff)
    return staff


@pytest_asyncio.fixture
async def inactive_staff(session: AsyncSession) -> Staff:
    staff = Staff(
        document_type="CC",
        document_number=unique_document_number(),
        first_name="Carlos",
        last_name="Diaz",
        is_active=False,
    )
    session.add(staff)
    await session.commit()
    await session.refresh(staff)
    return staff
