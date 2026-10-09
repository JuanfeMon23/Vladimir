"""Fixtures de test del modulo `result_templates`: BD real local, aislada
por test (`session`/`client` vienen de `app/conftest.py`).
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.result_templates import controller
from app.modules.result_templates.models import Unit
from app.modules.result_templates.schemas import (
    ResultTemplateCreate,
    ResultTemplateVersionCreate,
    ResultTemplateVersionRead,
)


def unique_code(prefix: str) -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes
    (prefijo `ZZ`: nada se borra, ni siquiera los datos de prueba)."""
    return f"ZZ{prefix}-{uuid4().hex[:24]}"


async def make_unit(
    session: AsyncSession, *, symbol: str = "mg/dL", is_active: bool = True
) -> Unit:
    unit = Unit(
        code=unique_code("unit"),
        symbol=symbol,
        name="Unidad de prueba",
        is_active=is_active,
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


@pytest_asyncio.fixture
async def unit(session: AsyncSession) -> Unit:
    return await make_unit(session)


@pytest.fixture
def unit_payload() -> dict:
    return {
        "code": unique_code("unit"),
        "symbol": "mmol/L",
        "name": "Milimoles por litro",
    }


@pytest.fixture
def analyte_payload(unit: Unit) -> dict:
    return {
        "code": unique_code("analyte"),
        "name": "Glucosa",
        "default_unit_id": str(unit.id),
    }


@pytest.fixture
def option_set_payload() -> dict:
    return {
        "code": unique_code("option-set"),
        "name": "Positivo/Negativo",
    }


@pytest.fixture
def option_payload() -> dict:
    return {
        "code": "positive",
        "label": "Positivo",
        "sort_order": 1,
        "is_abnormal": True,
    }


@pytest.fixture
def result_template_payload() -> dict:
    return {
        "code": unique_code("result-template"),
        "name": "Perfil basico",
        "description": "Plantilla de prueba",
    }


@pytest.fixture
def result_template_version_payload() -> dict:
    return {
        "report_settings": {"logo": True, "columns": 2},
    }


@pytest_asyncio.fixture
async def draft(
    session: AsyncSession,
    result_template_payload: dict,
    result_template_version_payload: dict,
) -> ResultTemplateVersionRead:
    """Version 1 en borrador de una plantilla nueva."""
    template = await controller.create_template(
        session, ResultTemplateCreate(**result_template_payload)
    )
    return await controller.create_version(
        session,
        template.id,
        ResultTemplateVersionCreate(**result_template_version_payload),
    )
