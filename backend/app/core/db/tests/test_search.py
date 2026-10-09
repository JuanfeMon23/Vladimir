"""Busqueda de texto insensible a mayusculas y tildes: `normalized()` y la
extension `unaccent` (sin indices trigram ni `pg_trgm`).
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.registry import Base
from app.core.db.search import normalized, normalized_pattern

from .conftest import unique_code


async def test_busqueda_con_tildes_y_mayusculas(session: AsyncSession) -> None:
    from app.modules.lab_areas.models import LabArea

    area_id = (
        await session.execute(
            text(
                "INSERT INTO lab_areas (code, name) "
                "VALUES (:c, 'Hematología') RETURNING id"
            ),
            {"c": unique_code("area")},
        )
    ).scalar_one()
    for term in ("hemato", "HEMATO", "hematología", "HEMATOLOGÍA", "matolog"):
        found = (
            await session.execute(
                select(LabArea.id).where(
                    LabArea.id == area_id,
                    normalized(LabArea.name).like(normalized_pattern(term)),
                )
            )
        ).scalar_one_or_none()
        assert found == area_id, term


def test_normalized_compila_a_unaccent_lower() -> None:
    from app.modules.lab_tests.models import LabTest

    assert str(normalized(LabTest.name).compile()) == "unaccent(lower(lab_tests.name))"


async def test_unaccent_quita_tildes(session: AsyncSession) -> None:
    value = (await session.execute(text("SELECT unaccent('Hematología')"))).scalar_one()
    assert value == "Hematologia"


async def test_no_existen_indices_trigram_ni_pg_trgm_pero_si_unaccent(
    session: AsyncSession,
) -> None:
    indexes = (
        await session.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
                r"AND indexname LIKE '%\_trgm'"
            )
        )
    ).all()
    assert indexes == []
    extensions = {
        row[0]
        for row in await session.execute(text("SELECT extname FROM pg_extension"))
    }
    assert "unaccent" in extensions
    assert "pg_trgm" not in extensions
    function = (
        await session.execute(
            text("SELECT count(*) FROM pg_proc WHERE proname = 'f_unaccent'")
        )
    ).scalar_one()
    assert function == 0


def test_los_modelos_no_declaran_indices_trigram() -> None:
    declared = [
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
        if index.name and index.name.endswith("_trgm")
    ]
    assert declared == []


@pytest.mark.parametrize("table", ["lab_tests", "analytes", "staff"])
async def test_tablas_sin_indice_trigram(session: AsyncSession, table: str) -> None:
    count = (
        await session.execute(
            text(
                "SELECT count(*) FROM pg_indexes WHERE tablename = :t "
                r"AND indexname LIKE '%\_trgm'"
            ),
            {"t": table},
        )
    ).scalar_one()
    assert count == 0
