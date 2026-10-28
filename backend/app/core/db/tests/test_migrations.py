"""Tests de la cadena de migraciones sobre una BD temporal propia
(`vladimir_migrations_test`), creada y eliminada por este modulo: nunca se
hace `downgrade` sobre la BD de desarrollo.

- `upgrade head` deja el esquema igual a `Base.metadata`.
- `downgrade base` -> `upgrade head` funciona (todo `downgrade` es real).
- Migraciones de datos: desactivacion + backfill de actividad (6be0a4509512)
  y texto de unidades -> catalogo `units` (98b5c90d1b86), ida y vuelta.
"""

import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import asyncpg
import pytest_asyncio
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db.registry import Base

BACKEND_DIR = Path(__file__).resolve().parents[4]
TEST_DB = "vladimir_migrations_test"

REV_LAB_TESTS = "db1a126fd56b"
REV_SOFT_DELETE = "6be0a4509512"
REV_UNITS = "98b5c90d1b86"


def _urls() -> tuple[str, str, str]:
    """(url SQLAlchemy de la BD de prueba, dsn asyncpg de prueba, dsn admin)."""
    base = make_url(get_settings().database_url)
    sa_url = base.set(database=TEST_DB).render_as_string(hide_password=False)
    plain = base.set(drivername="postgresql")
    test_dsn = plain.set(database=TEST_DB).render_as_string(hide_password=False)
    admin_dsn = plain.set(database="postgres").render_as_string(hide_password=False)
    return sa_url, test_dsn, admin_dsn


SA_URL, TEST_DSN, ADMIN_DSN = _urls()


def alembic(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={
            **os.environ,
            "DATABASE_URL": SA_URL,
            "MIGRATION_DATABASE_URL": SA_URL,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def _drop_test_db(admin: asyncpg.Connection) -> None:
    await admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def migrated_db() -> AsyncGenerator[None]:
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await _drop_test_db(admin)
        await admin.execute(f'CREATE DATABASE "{TEST_DB}"')
        alembic("upgrade", "head")
        yield
    finally:
        await _drop_test_db(admin)
        await admin.close()


@pytest_asyncio.fixture(loop_scope="session")
async def db(migrated_db: None) -> AsyncGenerator[asyncpg.Connection]:
    connection = await asyncpg.connect(TEST_DSN)
    try:
        yield connection
    finally:
        await connection.close()


async def _schema_diff() -> list:
    engine = create_async_engine(SA_URL)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync: compare_metadata(
                    MigrationContext.configure(sync), Base.metadata
                )
            )
    finally:
        await engine.dispose()


async def test_upgrade_head_coincide_con_los_modelos(migrated_db: None) -> None:
    assert await _schema_diff() == []


async def test_downgrade_base_y_upgrade_head_de_nuevo(db: asyncpg.Connection) -> None:
    alembic("upgrade", "head")
    alembic("downgrade", "base")
    tables = await db.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    )
    functions = await db.fetch(
        "SELECT proname FROM pg_proc WHERE proname LIKE 'fn\\_%'"
    )
    assert [row["tablename"] for row in tables] == ["alembic_version"]
    assert functions == []

    alembic("upgrade", "head")
    assert await _schema_diff() == []


async def test_migracion_de_desactivacion_hace_backfill_y_resuelve_duplicados(
    db: asyncpg.Connection,
) -> None:
    alembic("upgrade", "head")
    alembic("downgrade", REV_LAB_TESTS)
    area_id = await db.fetchval(
        "INSERT INTO lab_areas (code, name, is_active, created_at, updated_at) "
        "VALUES ('mig-area', 'Area', false, '2026-01-01', '2026-02-01') RETURNING id"
    )
    version_id = await db.fetchval(
        "WITH t AS (INSERT INTO result_templates (code, name) "
        "VALUES ('mig-rt', 'P') RETURNING id) "
        "INSERT INTO result_template_versions "
        "(result_template_id, version_number, report_settings) "
        "SELECT id, 1, '{}' FROM t RETURNING id"
    )
    analyte_id = await db.fetchval(
        "INSERT INTO analytes (code, name) VALUES ('mig-an', 'A') RETURNING id"
    )
    older, newer = [
        await db.fetchval(
            "INSERT INTO result_template_analytes "
            "(version_id, analyte_id, sort_order, result_type, created_at) "
            "VALUES ($1, $2, 1, 'numeric', $3::text::timestamptz) RETURNING id",
            version_id,
            analyte_id,
            created_at,
        )
        for created_at in ("2026-01-01", "2026-03-01")
    ]

    alembic("upgrade", REV_SOFT_DELETE)

    events = await db.fetch(
        "SELECT action, reason, occurred_at::date::text AS day FROM activity_events "
        "WHERE entity_id = $1 ORDER BY occurred_at",
        area_id,
    )
    assert [tuple(e) for e in events] == [
        ("activated", None, "2026-01-01"),
        ("deactivated", "migración: fecha aproximada", "2026-02-01"),
    ]
    active = await db.fetch(
        "SELECT id, is_active FROM result_template_analytes WHERE version_id = $1",
        version_id,
    )
    assert {row["id"]: row["is_active"] for row in active} == {
        older: True,
        newer: False,
    }

    # downgrade: lo inactivo de las tablas que ganaron is_active se elimina
    # (antes, quitar = borrar), lo activo se conserva.
    alembic("downgrade", REV_LAB_TESTS)
    remaining = await db.fetch(
        "SELECT id FROM result_template_analytes WHERE version_id = $1", version_id
    )
    assert [row["id"] for row in remaining] == [older]

    alembic("upgrade", "head")


async def test_migracion_de_unidades_convierte_texto_a_catalogo_y_vuelve(
    db: asyncpg.Connection,
) -> None:
    alembic("upgrade", "head")
    alembic("downgrade", REV_SOFT_DELETE)
    analytes = {
        text: await db.fetchval(
            "INSERT INTO analytes (code, name, default_unit) "
            "VALUES ($1, 'A', $2) RETURNING id",
            f"mig-unit-{i}",
            text,
        )
        for i, text in enumerate(["MG/DL", "µg/dL", "UnidadRara"])
    }

    alembic("upgrade", REV_UNITS)

    mapped = await db.fetch(
        "SELECT a.id, u.code, u.symbol, u.name FROM analytes a "
        "JOIN units u ON u.id = a.default_unit_id WHERE a.id = ANY($1::uuid[])",
        list(analytes.values()),
    )
    by_id = {row["id"]: row for row in mapped}
    assert by_id[analytes["MG/DL"]]["code"] == "mg/dL"
    assert by_id[analytes["µg/dL"]]["code"] == "ug/dL"
    assert tuple(by_id[analytes["UnidadRara"]])[1:] == (
        "UnidadRara",
        "UnidadRara",
        "UnidadRara",
    )

    alembic("downgrade", REV_SOFT_DELETE)
    restored = await db.fetch(
        "SELECT id, default_unit FROM analytes WHERE id = ANY($1::uuid[])",
        list(analytes.values()),
    )
    assert {row["id"]: row["default_unit"] for row in restored} == {
        analytes["MG/DL"]: "mg/dL",
        analytes["µg/dL"]: "µg/dL",
        analytes["UnidadRara"]: "UnidadRara",
    }

    alembic("upgrade", "head")
