"""Reglas de BD de "nada se borra, solo se desactiva" y del registro de
actividad (`activity_events`), sobre el esquema migrado (`upgrade head`).
"""

from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.registry import Base
from app.core.db.triggers import (
    ACTIVITY_REASON_SETTING,
    FORBIDDEN_OPERATION_SQLSTATE,
    activity_trigger_name,
    forbid_delete_trigger_name,
)

from .conftest import sqlstate, unique_code


async def _insert_area(session: AsyncSession, *, is_active: bool = True) -> UUID:
    return (
        await session.execute(
            text(
                "INSERT INTO lab_areas (code, name, is_active) "
                "VALUES (:code, 'Area de prueba', :is_active) RETURNING id"
            ),
            {"code": unique_code("area"), "is_active": is_active},
        )
    ).scalar_one()


async def _events(session: AsyncSession, entity_id: UUID) -> list[tuple]:
    rows = await session.execute(
        text(
            "SELECT entity_type, action, reason FROM activity_events "
            "WHERE entity_id = :id ORDER BY occurred_at, id"
        ),
        {"id": entity_id},
    )
    return [tuple(row) for row in rows]


async def _triggers(session: AsyncSession) -> set[tuple[str, str]]:
    rows = await session.execute(
        text(
            "SELECT c.relname, t.tgname FROM pg_trigger t "
            "JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal"
        )
    )
    return {(row[0], row[1]) for row in rows}


# --- cobertura de triggers en todo el esquema ---


async def test_toda_tabla_del_esquema_tiene_trigger_de_no_borrado(
    session: AsyncSession,
) -> None:
    triggers = await _triggers(session)
    missing = [
        table
        for table in Base.metadata.tables
        if (table, forbid_delete_trigger_name(table)) not in triggers
    ]
    assert missing == []


async def test_toda_tabla_con_is_active_tiene_trigger_de_actividad(
    session: AsyncSession,
) -> None:
    triggers = await _triggers(session)
    activatable = [
        name for name, table in Base.metadata.tables.items() if "is_active" in table.c
    ]
    assert "lab_test_preconditions" in activatable
    missing = [
        table
        for table in activatable
        if (table, activity_trigger_name(table)) not in triggers
    ]
    assert missing == []


# --- no borrado ---


async def test_delete_en_tabla_de_negocio_lanza_excepcion_identificable(
    session: AsyncSession,
) -> None:
    area_id = await _insert_area(session)

    with pytest.raises(DBAPIError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text("DELETE FROM lab_areas WHERE id = :id"), {"id": area_id}
            )

    assert sqlstate(exc_info.value) == FORBIDDEN_OPERATION_SQLSTATE
    assert "desactiv" in str(exc_info.value.orig)


async def test_activity_events_es_inmutable(session: AsyncSession) -> None:
    area_id = await _insert_area(session)

    for statement in (
        "DELETE FROM activity_events WHERE entity_id = :id",
        "UPDATE activity_events SET reason = 'x' WHERE entity_id = :id",
    ):
        with pytest.raises(DBAPIError) as exc_info:
            async with session.begin_nested():
                await session.execute(text(statement), {"id": area_id})
        assert sqlstate(exc_info.value) == FORBIDDEN_OPERATION_SQLSTATE


# --- registro de actividad ---


async def test_insert_activo_registra_activated_sin_motivo(
    session: AsyncSession,
) -> None:
    area_id = await _insert_area(session)

    assert await _events(session, area_id) == [("lab_areas", "activated", None)]


async def test_insert_inactivo_registra_deactivated(session: AsyncSession) -> None:
    area_id = await _insert_area(session, is_active=False)

    assert await _events(session, area_id) == [("lab_areas", "deactivated", None)]


async def test_cambio_de_is_active_registra_evento_con_motivo_de_la_transaccion(
    session: AsyncSession,
) -> None:
    area_id = await _insert_area(session)

    await session.execute(
        text("SELECT set_config(:name, 'Area cerrada', true)"),
        {"name": ACTIVITY_REASON_SETTING},
    )
    await session.execute(
        text("UPDATE lab_areas SET is_active = false WHERE id = :id"), {"id": area_id}
    )
    await session.execute(
        text("SELECT set_config(:name, '', true)"), {"name": ACTIVITY_REASON_SETTING}
    )
    await session.execute(
        text("UPDATE lab_areas SET is_active = true WHERE id = :id"), {"id": area_id}
    )

    assert await _events(session, area_id) == [
        ("lab_areas", "activated", None),
        ("lab_areas", "deactivated", "Area cerrada"),
        ("lab_areas", "activated", None),
    ]


async def test_update_sin_cambio_de_is_active_no_registra_evento(
    session: AsyncSession,
) -> None:
    area_id = await _insert_area(session)

    await session.execute(
        text("UPDATE lab_areas SET name = 'Otro', is_active = true WHERE id = :id"),
        {"id": area_id},
    )

    assert await _events(session, area_id) == [("lab_areas", "activated", None)]


# --- tablas puente del examen: PK sustituta + pareja unica ---


async def _lab_test_and_precondition(session: AsyncSession) -> tuple[UUID, UUID]:
    area_id = await _insert_area(session)
    lab_test_id = (
        await session.execute(
            text(
                "INSERT INTO lab_tests (code, name, area_id) "
                "VALUES (:code, 'Examen', :area_id) RETURNING id"
            ),
            {"code": unique_code("lab-test"), "area_id": area_id},
        )
    ).scalar_one()
    precondition_id = (
        await session.execute(
            text(
                "INSERT INTO preconditions (code, name, kind, category) "
                "VALUES (:code, 'Ayuno', 'precondition', 'ayuno') RETURNING id"
            ),
            {"code": unique_code("precond")},
        )
    ).scalar_one()
    return lab_test_id, precondition_id


async def test_lab_test_preconditions_tiene_id_propio_y_pareja_unica(
    session: AsyncSession,
) -> None:
    lab_test_id, precondition_id = await _lab_test_and_precondition(session)
    params = {"t": lab_test_id, "p": precondition_id}
    insert = text(
        "INSERT INTO lab_test_preconditions (lab_test_id, precondition_id, sort_order)"
        " VALUES (:t, :p, 1) RETURNING id, is_active"
    )

    row = (await session.execute(insert, params)).one()
    assert isinstance(row.id, UUID)
    assert row.is_active is True
    assert await _events(session, row.id) == [
        ("lab_test_preconditions", "activated", None)
    ]

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(insert, params)


# --- result_template_analytes: un analito activo por version ---


async def _template_version(session: AsyncSession) -> UUID:
    template_id = (
        await session.execute(
            text(
                "INSERT INTO result_templates (code, name) "
                "VALUES (:code, 'Plantilla') RETURNING id"
            ),
            {"code": unique_code("rt")},
        )
    ).scalar_one()
    return (
        await session.execute(
            text(
                "INSERT INTO result_template_versions "
                "(result_template_id, version_number, report_settings) "
                "VALUES (:id, 1, '{}') RETURNING id"
            ),
            {"id": template_id},
        )
    ).scalar_one()


async def _analyte(session: AsyncSession) -> UUID:
    return (
        await session.execute(
            text(
                "INSERT INTO analytes (code, name) VALUES (:code, 'Glucosa') RETURNING id"
            ),
            {"code": unique_code("analyte")},
        )
    ).scalar_one()


_INSERT_TEMPLATE_ANALYTE = text(
    "INSERT INTO result_template_analytes "
    "(version_id, analyte_id, sort_order, result_type, is_active) "
    "VALUES (:v, :a, 1, 'numeric', :is_active) RETURNING id"
)


async def test_mismo_analito_activo_dos_veces_en_una_version_falla(
    session: AsyncSession,
) -> None:
    params = {
        "v": await _template_version(session),
        "a": await _analyte(session),
        "is_active": True,
    }
    await session.execute(_INSERT_TEMPLATE_ANALYTE, params)

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(_INSERT_TEMPLATE_ANALYTE, params)


async def test_mismo_analito_inactivo_y_activo_en_una_version_se_permite(
    session: AsyncSession,
) -> None:
    version_id = await _template_version(session)
    analyte_id = await _analyte(session)

    await session.execute(
        _INSERT_TEMPLATE_ANALYTE, {"v": version_id, "a": analyte_id, "is_active": False}
    )
    await session.execute(
        _INSERT_TEMPLATE_ANALYTE, {"v": version_id, "a": analyte_id, "is_active": True}
    )


# --- reference_ranges: coherencia de limites ---


@pytest.mark.parametrize(
    "values",
    [
        {"low": 10, "high": 5},
        {"critical_low": 6, "low": 5},
        {"high": 10, "critical_high": 9},
        {"age_min": 18, "age_max": 1},
    ],
    ids=["low>high", "critical_low>low", "high>critical_high", "age_min>age_max"],
)
async def test_rango_de_referencia_con_limites_invertidos_falla(
    session: AsyncSession, values: dict
) -> None:
    template_analyte_id = (
        await session.execute(
            _INSERT_TEMPLATE_ANALYTE,
            {
                "v": await _template_version(session),
                "a": await _analyte(session),
                "is_active": True,
            },
        )
    ).scalar_one()
    columns = ", ".join(values)
    placeholders = ", ".join(f":{c}" for c in values)

    with pytest.raises(IntegrityError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text(
                    f"INSERT INTO reference_ranges (template_analyte_id, sex, {columns})"
                    f" VALUES (:ta, 'any', {placeholders})"
                ),
                {"ta": template_analyte_id, **values},
            )
    assert sqlstate(exc_info.value) == "23514"


async def test_rango_de_referencia_con_extremos_nulos_o_iguales_se_permite(
    session: AsyncSession,
) -> None:
    template_analyte_id = (
        await session.execute(
            _INSERT_TEMPLATE_ANALYTE,
            {
                "v": await _template_version(session),
                "a": await _analyte(session),
                "is_active": True,
            },
        )
    ).scalar_one()

    await session.execute(
        text(
            "INSERT INTO reference_ranges "
            "(template_analyte_id, sex, low, high, critical_low, critical_high,"
            " age_min, age_max) VALUES "
            "(:ta, 'any', NULL, 200, 50, NULL, 18, 18),"
            "(:ta, 'male', 5, 5, 5, 5, NULL, 65)"
        ),
        {"ta": template_analyte_id},
    )


# --- lab_test_sample_types: un preferido activo por examen ---


async def _sample_type(session: AsyncSession) -> UUID:
    sample_id = (
        await session.execute(
            text("INSERT INTO samples (code, name) VALUES (:c, 'Sangre') RETURNING id"),
            {"c": unique_code("sample")},
        )
    ).scalar_one()
    return (
        await session.execute(
            text(
                "INSERT INTO sample_types (sample_id, code, name, specimen) "
                "VALUES (:s, :c, 'Tubo', 'suero') RETURNING id"
            ),
            {"s": sample_id, "c": unique_code("sample-type")},
        )
    ).scalar_one()


_INSERT_LAB_TEST_SAMPLE_TYPE = text(
    "INSERT INTO lab_test_sample_types "
    "(lab_test_id, sample_type_id, is_preferred, sort_order, is_active) "
    "VALUES (:t, :s, true, 1, :is_active)"
)


async def test_preferido_desactivado_no_bloquea_otro_preferido(
    session: AsyncSession,
) -> None:
    lab_test_id, _ = await _lab_test_and_precondition(session)

    await session.execute(
        _INSERT_LAB_TEST_SAMPLE_TYPE,
        {"t": lab_test_id, "s": await _sample_type(session), "is_active": False},
    )
    await session.execute(
        _INSERT_LAB_TEST_SAMPLE_TYPE,
        {"t": lab_test_id, "s": await _sample_type(session), "is_active": True},
    )

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(
                _INSERT_LAB_TEST_SAMPLE_TYPE,
                {"t": lab_test_id, "s": await _sample_type(session), "is_active": True},
            )
