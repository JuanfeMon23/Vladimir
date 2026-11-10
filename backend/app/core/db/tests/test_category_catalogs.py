"""Catalogos de categoria (regla «Catalogos en BD», 2026-11-09): cada lista
seleccionable que antes era un `CHECK` con tupla es una tabla de catalogo y la
columna que la usa es una FK al `code` del catalogo (mismos codigos, datos sin
cambios).
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.seeds.catalogs import CATALOGS, seed_catalogs

from .conftest import sqlstate, unique_code

# Valores que tenian los CHECK antes de la migracion (no deben cambiar).
FORMER_CHECK_VALUES: dict[str, set[str]] = {
    "consent_document_types": {"consentimiento_informado", "tratamiento_datos", "otro"},
    "consent_signers": {"paciente", "paciente_o_representante"},
    "duration_units": {"minutos", "horas", "dias"},
    "precondition_kinds": {"precondition", "condition"},
    "precondition_categories": {
        "ayuno",
        "dieta",
        "alcohol_sustancias",
        "tabaco",
        "medicamentos",
        "actividad_fisica",
        "abstinencia_sexual",
        "recoleccion_muestra",
        "horario_toma",
        "reposo",
        "higiene",
        "otro",
    },
    "specimen_types": {
        "suero",
        "plasma",
        "sangre_total",
        "orina",
        "heces",
        "secrecion",
        "otro",
    },
    "result_types": {
        "numeric",
        "boolean",
        "qualitative",
        "semi_quantitative",
        "titer",
        "text",
        "calculated",
    },
    "sexes": {"any", "male", "female"},
    "age_units": {"dias", "meses", "anos"},
}

# (tabla, columna, catalogo)
CATEGORY_COLUMNS = [
    ("consent_documents", "document_type", "consent_document_types"),
    ("consent_document_versions", "signer", "consent_signers"),
    ("preconditions", "kind", "precondition_kinds"),
    ("preconditions", "category", "precondition_categories"),
    ("preconditions", "duration_unit", "duration_units"),
    ("lab_test_preconditions", "duration_unit_override", "duration_units"),
    ("sample_types", "specimen", "specimen_types"),
    ("result_template_analytes", "result_type", "result_types"),
    ("reference_ranges", "sex", "sexes"),
    ("reference_ranges", "age_unit", "age_units"),
]


def test_la_semilla_cubre_exactamente_los_catalogos_esperados() -> None:
    assert {seed.table for seed in CATALOGS} == set(FORMER_CHECK_VALUES)
    for seed in CATALOGS:
        assert {row[0] for row in seed.rows} == FORMER_CHECK_VALUES[seed.table]


@pytest.mark.parametrize("table", sorted(FORMER_CHECK_VALUES))
async def test_catalogo_sembrado_con_los_mismos_codes(
    session: AsyncSession, table: str
) -> None:
    rows = (
        await session.execute(
            text(f"SELECT code, name, sort_order, is_active FROM {table}")
        )
    ).all()

    assert FORMER_CHECK_VALUES[table] <= {row.code for row in rows}
    seeded = [row for row in rows if row.code in FORMER_CHECK_VALUES[table]]
    assert all(row.name.strip() and row.is_active for row in seeded)
    assert len({row.sort_order for row in seeded}) == len(seeded)


@pytest.mark.parametrize(("table", "column", "catalog"), CATEGORY_COLUMNS)
async def test_columna_de_categoria_es_fk_al_code_y_ya_no_tiene_check(
    session: AsyncSession, table: str, column: str, catalog: str
) -> None:
    fk = (
        await session.execute(
            text(
                "SELECT confrelid::regclass::text AS target, "
                "pg_get_constraintdef(oid) AS definition "
                "FROM pg_constraint WHERE contype = 'f' "
                "AND conrelid = CAST(:t AS regclass) AND conname = :n"
            ),
            {"t": table, "n": f"fk_{table}_{column}_{catalog}"},
        )
    ).one()
    assert fk.target == catalog
    assert f"FOREIGN KEY ({column})" in fk.definition
    assert "(code)" in fk.definition

    check = (
        await session.execute(
            text(
                "SELECT 1 FROM pg_constraint WHERE contype = 'c' "
                "AND conrelid = CAST(:t AS regclass) AND conname = :n"
            ),
            {"t": table, "n": f"ck_{table}_{column}"},
        )
    ).first()
    assert check is None


async def test_precondicion_con_categoria_fuera_del_catalogo_viola_fk(
    session: AsyncSession,
) -> None:
    insert = text(
        "INSERT INTO preconditions (code, name, kind, category) "
        "VALUES (:c, 'P', :kind, :category)"
    )
    with pytest.raises(IntegrityError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                insert,
                {
                    "c": unique_code("p"),
                    "kind": "precondition",
                    "category": "inventada",
                },
            )
    assert sqlstate(exc_info.value) == "23503"

    await session.execute(
        insert,
        {"c": unique_code("p"), "kind": "precondition", "category": "ayuno"},
    )


async def test_un_valor_nuevo_del_catalogo_se_puede_usar_sin_tocar_el_esquema(
    session: AsyncSession,
) -> None:
    specimen = f"liquido_{uuid4().hex[:8]}"
    await session.execute(
        text(
            "INSERT INTO specimen_types (code, name, sort_order) "
            "VALUES (:c, 'Liquido', 900)"
        ),
        {"c": specimen},
    )
    sample_id = (
        await session.execute(
            text("INSERT INTO samples (code, name) VALUES (:c, 'S') RETURNING id"),
            {"c": unique_code("s")},
        )
    ).scalar_one()

    await session.execute(
        text(
            "INSERT INTO sample_types (code, sample_id, name, specimen) "
            "VALUES (:c, :s, 'T', :sp)"
        ),
        {"c": unique_code("st"), "s": sample_id, "sp": specimen},
    )


async def test_documento_de_consentimiento_con_tipo_fuera_del_catalogo_viola_fk(
    session: AsyncSession,
) -> None:
    with pytest.raises(IntegrityError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO consent_documents (code, name, document_type) "
                    "VALUES (:c, 'D', 'inventado')"
                ),
                {"c": unique_code("cd")},
            )
    assert sqlstate(exc_info.value) == "23503"


async def test_sexo_comodin_unico_y_marcado(session: AsyncSession) -> None:
    rows = (
        await session.execute(
            text("SELECT code FROM sexes WHERE is_wildcard ORDER BY code")
        )
    ).all()
    assert [row.code for row in rows] == ["any"]

    with pytest.raises(IntegrityError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO sexes (code, name, sort_order, is_wildcard) "
                    "VALUES (:c, 'Otro comodin', 99, true)"
                ),
                {"c": unique_code("sx")},
            )
    assert sqlstate(exc_info.value) == "23505"


async def test_unidades_de_edad_y_duracion_traen_su_factor_de_conversion(
    session: AsyncSession,
) -> None:
    age = {
        row.code: float(row.days)
        for row in await session.execute(text("SELECT code, days FROM age_units"))
    }
    assert (age["dias"], age["meses"], age["anos"]) == (1.0, 30.4375, 365.25)

    duration = {
        row.code: row.minutes
        for row in await session.execute(
            text("SELECT code, minutes FROM duration_units")
        )
    }
    assert (duration["minutos"], duration["horas"], duration["dias"]) == (1, 60, 1440)

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO age_units (code, name, sort_order, days) "
                    "VALUES (:c, 'Cero', 99, 0)"
                ),
                {"c": unique_code("au")},
            )


async def test_tipos_de_resultado_traen_su_comportamiento(
    session: AsyncSession,
) -> None:
    rows = {
        row.code: row
        for row in await session.execute(text("SELECT * FROM result_types"))
    }

    option_set = {c for c, r in rows.items() if r.uses_option_set}
    assert {"qualitative", "semi_quantitative", "titer"} <= option_set
    assert "numeric" not in option_set

    numeric_range = {c for c, r in rows.items() if r.uses_numeric_range}
    assert {"numeric", "calculated"} <= numeric_range
    assert {c for c, r in rows.items() if r.uses_boolean_range} >= {"boolean"}
    assert {c for c, r in rows.items() if r.uses_unit} >= {"numeric", "calculated"}
    assert {c for c, r in rows.items() if r.uses_formula} >= {"calculated"}
    assert {c for c, r in rows.items() if r.requires_reference_range} >= {"numeric"}
    assert not rows["text"].uses_option_set
    assert not rows["text"].uses_numeric_range


async def test_seed_catalogs_es_idempotente_y_no_pisa_ediciones(
    session: AsyncSession,
) -> None:
    await session.execute(
        text(
            "UPDATE specimen_types SET name = 'Editado', is_active = false "
            "WHERE code = 'suero'"
        )
    )

    await session.run_sync(lambda s: seed_catalogs(s.connection()))
    await session.run_sync(lambda s: seed_catalogs(s.connection()))

    suero = (
        await session.execute(
            text("SELECT name, is_active FROM specimen_types WHERE code = 'suero'")
        )
    ).one()
    assert (suero.name, suero.is_active) == ("Editado", False)
    for table in FORMER_CHECK_VALUES:
        duplicated = (
            await session.execute(
                text(f"SELECT code FROM {table} GROUP BY code HAVING count(*) > 1")
            )
        ).all()
        assert duplicated == []
