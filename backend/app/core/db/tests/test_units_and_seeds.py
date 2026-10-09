"""Catalogo `units` (UCUM) y semillas idempotentes de unidades y conjuntos
de opciones de resultado."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.seeds.result_option_sets import (
    RESULT_OPTION_SETS,
    seed_result_option_sets,
)
from app.core.db.seeds.units import UNITS, seed_units

from .conftest import sqlstate, unique_code


async def test_la_migracion_deja_cargadas_las_unidades_ucum_semilla(
    session: AsyncSession,
) -> None:
    rows = await session.execute(text("SELECT code, symbol, name FROM units"))
    by_code = {row.code: row for row in rows}

    missing = [unit.code for unit in UNITS if unit.code not in by_code]
    assert missing == []
    assert by_code["ug/dL"].symbol == "µg/dL"
    assert by_code["10*3/uL"].symbol == "×10³/µL"


async def test_seed_units_es_idempotente(session: AsyncSession) -> None:
    await session.run_sync(lambda s: seed_units(s.connection()))
    await session.run_sync(lambda s: seed_units(s.connection()))

    duplicated = (
        await session.execute(
            text("SELECT code FROM units GROUP BY code HAVING count(*) > 1")
        )
    ).all()
    assert duplicated == []


async def test_code_de_unidad_distingue_mayusculas_como_ucum(
    session: AsyncSession,
) -> None:
    code = f"u{uuid4().hex[:8]}"
    insert = text("INSERT INTO units (code, symbol, name) VALUES (:c, :c, :c)")
    await session.execute(insert, {"c": code})
    await session.execute(insert, {"c": code.upper()})

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(insert, {"c": code})


async def test_unidad_inexistente_viola_fk(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO analytes (code, name, default_unit_id) "
                    "VALUES (:code, 'X', uuidv7())"
                ),
                {"code": unique_code("analyte")},
            )
    assert sqlstate(exc_info.value) == "23503"


async def test_analito_y_analito_de_plantilla_referencian_unidad(
    session: AsyncSession,
) -> None:
    unit_id = (
        await session.execute(text("SELECT id FROM units WHERE code = 'mg/dL'"))
    ).scalar_one()
    analyte_id = (
        await session.execute(
            text(
                "INSERT INTO analytes (code, name, default_unit_id) "
                "VALUES (:code, 'Glucosa', :u) RETURNING id"
            ),
            {"code": unique_code("analyte"), "u": unit_id},
        )
    ).scalar_one()
    template_id = (
        await session.execute(
            text(
                "INSERT INTO result_templates (code, name) VALUES (:c, 'P') RETURNING id"
            ),
            {"c": unique_code("rt")},
        )
    ).scalar_one()
    version_id = (
        await session.execute(
            text(
                "INSERT INTO result_template_versions "
                "(result_template_id, version_number, report_settings) "
                "VALUES (:t, 1, '{}') RETURNING id"
            ),
            {"t": template_id},
        )
    ).scalar_one()

    await session.execute(
        text(
            "INSERT INTO result_template_analytes "
            "(version_id, analyte_id, sort_order, result_type, unit_id, decimals) "
            "VALUES (:v, :a, 1, 'numeric', :u, 0)"
        ),
        {"v": version_id, "a": analyte_id, "u": unit_id},
    )


async def test_seed_de_conjuntos_de_opciones_es_idempotente_y_marca_anormales(
    session: AsyncSession,
) -> None:
    await session.run_sync(lambda s: seed_result_option_sets(s.connection()))
    await session.run_sync(lambda s: seed_result_option_sets(s.connection()))

    rows = await session.execute(
        text(
            "SELECT s.code AS set_code, o.code, o.label, o.sort_order, o.is_abnormal "
            "FROM result_option_sets s JOIN result_options o ON o.option_set_id = s.id "
            "WHERE s.code = ANY(:codes) ORDER BY s.code, o.sort_order"
        ),
        {"codes": [option_set.code for option_set in RESULT_OPTION_SETS]},
    )
    by_set: dict[str, list] = {}
    for row in rows:
        by_set.setdefault(row.set_code, []).append(row)

    assert [(o.label, o.is_abnormal) for o in by_set["reactividad"]] == [
        ("No reactivo", False),
        ("Reactivo", True),
        ("Indeterminado", True),
    ]
    assert [(o.label, o.is_abnormal) for o in by_set["positividad"]] == [
        ("Negativo", False),
        ("Positivo", True),
    ]
    assert [(o.label, o.is_abnormal) for o in by_set["cruces"]] == [
        ("Negativo", False),
        ("Trazas", False),
        ("+", True),
        ("++", True),
        ("+++", True),
        ("++++", True),
    ]
    assert [(o.label, o.is_abnormal) for o in by_set["presencia"]] == [
        ("Ausente", False),
        ("Presente", True),
    ]


async def test_seed_de_titulos_y_uroanalisis_queda_ordenado_y_marca_anormales(
    session: AsyncSession,
) -> None:
    await session.run_sync(lambda s: seed_result_option_sets(s.connection()))
    await session.run_sync(lambda s: seed_result_option_sets(s.connection()))

    rows = await session.execute(
        text(
            "SELECT s.code AS set_code, o.code, o.label, o.sort_order, o.is_abnormal "
            "FROM result_option_sets s JOIN result_options o ON o.option_set_id = s.id "
            "WHERE s.code IN ('titulos', 'color_orina', 'aspecto_orina') "
            "ORDER BY s.code, o.sort_order"
        )
    )
    by_set: dict[str, list] = {}
    for row in rows:
        by_set.setdefault(row.set_code, []).append(row)

    titulos = by_set["titulos"]
    assert [o.label for o in titulos] == [
        "No reactivo",
        "1:2",
        "1:4",
        "1:8",
        "1:16",
        "1:32",
        "1:64",
        "1:128",
        "1:256",
        "1:512",
        "1:1024",
        ">1:1024",
    ]
    assert [o.sort_order for o in titulos] == list(range(1, 13))
    assert not any(o.is_abnormal for o in titulos)
    assert [o.code for o in titulos][:3] == ["no_reactivo", "1_2", "1_4"]
    assert titulos[-1].code == "gt_1_1024"

    assert [(o.label, o.is_abnormal) for o in by_set["color_orina"]] == [
        ("Incoloro", False),
        ("Amarillo claro", False),
        ("Amarillo", False),
        ("Amarillo oscuro", False),
        ("Ámbar", False),
        ("Naranja", False),
        ("Rojizo", True),
        ("Marrón", True),
    ]
    assert [(o.label, o.is_abnormal) for o in by_set["aspecto_orina"]] == [
        ("Transparente", False),
        ("Ligeramente turbio", False),
        ("Turbio", True),
    ]
