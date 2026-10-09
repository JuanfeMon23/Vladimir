"""Tests de `core/activation.py` (motivo de (des)activacion, `ensure_active`,
`get_active_by_id`), del filtro de activos y del mapeo de `VLD01`."""

import json
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import (
    InactiveReferenceError,
    ensure_active,
    flush_with_reason,
    get_active_by_id,
)
from app.core.database import engine
from app.core.db.activity import ActivityEvent
from app.core.dependencies import ActiveOnlyFilter
from app.core.exceptions import db_error_handler
from app.core.schemas import ActivityReasonInput
from app.modules.lab_areas.models import LabArea


def _code() -> str:
    return f"ZZ-core-{uuid4().hex[:20]}"


async def _area(session: AsyncSession, *, is_active: bool = True) -> LabArea:
    area = LabArea(code=_code(), name="Area de prueba", is_active=is_active)
    session.add(area)
    await session.commit()
    return area


async def _events(session: AsyncSession, entity_id: UUID) -> list[tuple[str, str]]:
    rows = await session.execute(
        select(ActivityEvent.action, ActivityEvent.reason)
        .where(ActivityEvent.entity_id == entity_id)
        .order_by(ActivityEvent.occurred_at, ActivityEvent.id)
    )
    return [tuple(row) for row in rows]


async def test_flush_with_reason_registra_el_motivo_en_activity_events(
    session: AsyncSession,
) -> None:
    area = await _area(session)

    area.is_active = False
    await flush_with_reason(session, "Area cerrada")
    await session.commit()

    assert await _events(session, area.id) == [
        ("activated", None),
        ("deactivated", "Area cerrada"),
    ]


async def test_flush_with_reason_no_filtra_el_motivo_a_cambios_posteriores(
    session: AsyncSession,
) -> None:
    area = await _area(session)
    area.is_active = False
    await flush_with_reason(session, "Motivo 1")

    area.is_active = True
    await flush_with_reason(session, None)
    other = await _area(session)

    assert (await _events(session, area.id))[-1] == ("activated", None)
    assert await _events(session, other.id) == [("activated", None)]


async def test_ensure_active_lanza_inactive_reference_con_codigo(
    session: AsyncSession,
) -> None:
    area = await _area(session, is_active=False)

    with pytest.raises(InactiveReferenceError) as exc_info:
        ensure_active(area, subject="el área", field="area_id", feminine=True)

    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "inactive_reference"
    assert error.message == f"El área «{area.code}» está inactiva."
    assert error.details == {"area_id": str(area.id)}


async def test_ensure_active_no_hace_nada_si_esta_activo(
    session: AsyncSession,
) -> None:
    area = await _area(session)
    ensure_active(area, subject="el área", field="area_id", feminine=True)


async def test_get_active_by_id_ignora_inactivos_e_inexistentes(
    session: AsyncSession,
) -> None:
    active = await _area(session)
    inactive = await _area(session, is_active=False)

    assert await get_active_by_id(session, LabArea, active.id) is active
    assert await get_active_by_id(session, LabArea, inactive.id) is None
    assert await get_active_by_id(session, LabArea, uuid4()) is None


async def test_active_only_filter_apply(session: AsyncSession) -> None:
    active = await _area(session)
    inactive = await _area(session, is_active=False)
    ids = [active.id, inactive.id]
    base = select(LabArea.id).where(LabArea.id.in_(ids))

    async def run(flag: bool | None) -> set[UUID]:
        stmt = ActiveOnlyFilter(active=flag).apply(base, LabArea.is_active)
        return set((await session.execute(stmt)).scalars())

    assert await run(None) == {active.id, inactive.id}
    assert await run(True) == {active.id}
    assert await run(False) == {inactive.id}


def test_activity_reason_input_limita_a_255() -> None:
    assert ActivityReasonInput(activity_reason="x" * 255).activity_reason
    with pytest.raises(ValueError):
        ActivityReasonInput(activity_reason="x" * 256)


async def test_delete_bloqueado_por_bd_se_traduce_a_409_delete_forbidden(
    session: AsyncSession,
) -> None:
    area = await _area(session)

    with pytest.raises(DBAPIError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text("DELETE FROM lab_areas WHERE id = :id"), {"id": area.id}
            )

    response = db_error_handler(None, exc_info.value)  # type: ignore[arg-type]
    body = json.loads(response.body)
    assert response.status_code == 409
    assert body["code"] == "delete_forbidden"
    assert body["details"] == {"table": "lab_areas"}
    assert "desactiva" in body["message"]


@pytest.fixture
def executed_sql() -> Iterator[list[str]]:
    """Sentencias SQL que llegan a la BD mientras dura el test."""
    statements: list[str] = []

    def record(_conn, _cursor, statement, *_args) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    yield statements
    event.remove(engine.sync_engine, "before_cursor_execute", record)


async def test_patch_sin_is_active_no_fija_el_motivo_de_actividad(
    session: AsyncSession, client: AsyncClient, executed_sql: list[str]
) -> None:
    area = await _area(session)
    executed_sql.clear()

    response = await client.patch(
        f"/api/v1/lab-areas/{area.id}", json={"name": "Otro nombre"}
    )

    assert response.status_code == 200
    assert not any("set_config" in sql for sql in executed_sql)


async def test_patch_con_is_active_fija_el_motivo_una_sola_vez_y_lo_registra(
    session: AsyncSession, client: AsyncClient, executed_sql: list[str]
) -> None:
    area = await _area(session)
    executed_sql.clear()

    response = await client.patch(
        f"/api/v1/lab-areas/{area.id}",
        json={"is_active": False, "activity_reason": "Area cerrada"},
    )

    assert response.status_code == 200
    assert sum("set_config" in sql for sql in executed_sql) == 1
    assert (await _events(session, area.id))[-1] == ("deactivated", "Area cerrada")
