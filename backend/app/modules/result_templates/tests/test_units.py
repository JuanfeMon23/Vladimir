"""Catalogo de unidades (UCUM) y su uso en analitos."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.exceptions import CodeConflictError, NotFoundError
from app.modules.result_templates import controller
from app.modules.result_templates.models import Unit
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    AnalyteUpdate,
    UnitCreate,
)
from app.modules.result_templates.tests.conftest import make_unit, unique_code

# --- CRUD /units ---


async def test_list_units_includes_seed(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/units", params={"page_size": 200, "active": True}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 30
    by_code = {item["code"]: item for item in body["items"]}
    assert by_code["mg/dL"]["symbol"] == "mg/dL"
    assert by_code["10*3/uL"]["symbol"] == "×10³/µL"


async def test_create_get_and_patch_unit(
    client: AsyncClient, unit_payload: dict
) -> None:
    created = await client.post("/api/v1/units", json=unit_payload)
    assert created.status_code == 201
    unit_id = created.json()["id"]

    fetched = await client.get(f"/api/v1/units/{unit_id}")
    assert fetched.json()["symbol"] == "mmol/L"

    patched = await client.patch(
        f"/api/v1/units/{unit_id}",
        json={"is_active": False, "activity_reason": "Duplicada"},
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    activity = await client.get(
        "/api/v1/activity", params={"entity_type": "units", "entity_id": unit_id}
    )
    assert activity.json()["items"][0]["reason"] == "Duplicada"


async def test_create_unit_duplicate_code_returns_409(
    client: AsyncClient, unit_payload: dict
) -> None:
    await client.post("/api/v1/units", json=unit_payload)

    second = await client.post("/api/v1/units", json=unit_payload)

    assert second.status_code == 409
    assert second.json()["details"] == {"code": unit_payload["code"]}


async def test_unit_code_is_case_sensitive(session: AsyncSession) -> None:
    code = unique_code("u").lower()
    await controller.create_unit(
        session, UnitCreate(code=code, symbol="a", name="minuscula")
    )
    await controller.create_unit(
        session, UnitCreate(code=code.upper(), symbol="A", name="mayuscula")
    )

    with pytest.raises(CodeConflictError, match="Ya existe una unidad con el código"):
        await controller.create_unit(
            session, UnitCreate(code=code, symbol="a", name="otra")
        )


async def test_get_unit_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe una unidad con id"):
        await controller.get_unit(session, uuid4())


async def test_units_have_no_delete(client: AsyncClient, unit: Unit) -> None:
    response = await client.delete(f"/api/v1/units/{unit.id}")
    assert response.status_code == 405


# --- unidad del analito ---


async def test_analyte_read_exposes_unit_symbol_and_detail(
    session: AsyncSession, analyte_payload: dict, unit: Unit
) -> None:
    created = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    assert created.default_unit_id == unit.id
    assert created.default_unit == "mg/dL"
    assert created.default_unit_detail is not None
    assert created.default_unit_detail.model_dump() == {
        "id": unit.id,
        "code": unit.code,
        "symbol": unit.symbol,
        "name": unit.name,
    }


async def test_analyte_without_unit(
    session: AsyncSession, analyte_payload: dict
) -> None:
    created = await controller.create_analyte(
        session, AnalyteCreate(**{**analyte_payload, "default_unit_id": None})
    )
    assert created.default_unit is None
    assert created.default_unit_detail is None


async def test_create_analyte_with_unknown_unit_returns_422(
    client: AsyncClient, analyte_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/analytes",
        json={**analyte_payload, "default_unit_id": str(uuid4())},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"
    assert set(response.json()["details"]) == {"default_unit_id"}


async def test_create_analyte_with_inactive_unit_raises(
    session: AsyncSession, analyte_payload: dict
) -> None:
    inactive = await make_unit(session, is_active=False)

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_analyte(
            session,
            AnalyteCreate(**{**analyte_payload, "default_unit_id": inactive.id}),
        )
    assert exc_info.value.details == {"default_unit_id": str(inactive.id)}


async def test_update_analyte_keeping_its_now_inactive_unit_is_allowed(
    session: AsyncSession, analyte_payload: dict, unit: Unit
) -> None:
    created = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))
    unit.is_active = False
    await session.commit()

    updated = await controller.update_analyte(
        session,
        created.id,
        AnalyteUpdate(name="Glucosa basal", default_unit_id=unit.id),
    )
    assert updated.default_unit_id == unit.id


async def test_update_analyte_to_inactive_unit_raises(
    session: AsyncSession, analyte_payload: dict
) -> None:
    created = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))
    inactive = await make_unit(session, is_active=False)

    with pytest.raises(InactiveReferenceError):
        await controller.update_analyte(
            session, created.id, AnalyteUpdate(default_unit_id=inactive.id)
        )


async def test_analyte_write_does_not_accept_unit_string(
    client: AsyncClient, analyte_payload: dict
) -> None:
    """Escritura solo por `default_unit_id`; `default_unit` (texto) es de
    solo lectura y se ignora si llega en el body."""
    response = await client.post(
        "/api/v1/analytes",
        json={**analyte_payload, "default_unit_id": None, "default_unit": "mg/dL"},
    )
    assert response.status_code == 201
    assert response.json()["default_unit"] is None


async def test_deactivate_analyte_with_reason_appears_in_activity(
    client: AsyncClient, analyte_payload: dict
) -> None:
    analyte_id = (await client.post("/api/v1/analytes", json=analyte_payload)).json()[
        "id"
    ]

    await client.patch(
        f"/api/v1/analytes/{analyte_id}",
        json={"is_active": False, "activity_reason": "Reemplazado por GLU2"},
    )

    events = (
        await client.get(
            "/api/v1/activity",
            params={"entity_type": "analytes", "entity_id": analyte_id},
        )
    ).json()["items"]
    assert (events[0]["action"], events[0]["reason"]) == (
        "deactivated",
        "Reemplazado por GLU2",
    )
