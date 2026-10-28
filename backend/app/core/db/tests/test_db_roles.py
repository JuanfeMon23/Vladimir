"""`deploy/db_roles.sql`: roles de minimo privilegio.

Corre el script contra una BD temporal (`vladimir_roles_test`, migrada con
`MIGRATION_DATABASE_URL` mientras `DATABASE_URL` apunta a un servidor
inexistente, para probar tambien `migrations/env.py`) y verifica con
`SET ROLE` lo que `vladimir_app` puede y no puede hacer. Si los roles no
existian en el servidor, el test los borra al terminar.
"""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.engine import make_url

from app.core.db.tests.test_migrations import ADMIN_DSN, BACKEND_DIR

ROLES_DB = "vladimir_roles_test"
ROLES = ("vladimir_app", "vladimir_migrator")
SCRIPT = (BACKEND_DIR / "deploy" / "db_roles.sql").read_text(encoding="utf-8")
INSUFFICIENT_PRIVILEGE = "42501"
APPEND_ONLY = ("activity_events", "settings_history")


def _dsn(database: str, driver: str) -> str:
    url = make_url(ADMIN_DSN).set(drivername=driver, database=database)
    return url.render_as_string(hide_password=False)


async def _sqlstate(conn: asyncpg.Connection, role: str, sql: str) -> str | None:
    """SQLSTATE con que falla `sql` ejecutado como `role` (None si funciona)."""
    await conn.execute(f"SET ROLE {role}")
    try:
        await conn.execute(sql)
    except asyncpg.PostgresError as exc:
        return exc.sqlstate
    finally:
        await conn.execute("RESET ROLE")
    return None


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def roles_db() -> AsyncGenerator[asyncpg.Connection]:
    admin = await asyncpg.connect(ADMIN_DSN)
    existing = {
        r["rolname"]
        for r in await admin.fetch(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY($1::text[])",
            list(ROLES),
        )
    }
    await admin.execute(f'DROP DATABASE IF EXISTS "{ROLES_DB}" WITH (FORCE)')
    await admin.execute(f'CREATE DATABASE "{ROLES_DB}"')
    conn = None
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env={
                **os.environ,
                "DATABASE_URL": "postgresql+asyncpg://nadie:x@127.0.0.1:1/nada",
                "MIGRATION_DATABASE_URL": _dsn(ROLES_DB, "postgresql+asyncpg"),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        conn = await asyncpg.connect(_dsn(ROLES_DB, "postgresql"))
        await conn.execute(SCRIPT)
        yield conn
    finally:
        if conn is not None:
            await conn.close()
        await admin.execute(f'DROP DATABASE IF EXISTS "{ROLES_DB}" WITH (FORCE)')
        for role in ROLES:
            if role not in existing:
                await admin.execute(f"DROP ROLE IF EXISTS {role}")
        await admin.close()


async def test_alembic_uso_migration_database_url(roles_db) -> None:
    assert await roles_db.fetchval("SELECT count(*) FROM alembic_version") == 1


async def test_el_script_es_idempotente(roles_db) -> None:
    await roles_db.execute(SCRIPT)
    await roles_db.execute(SCRIPT)


async def test_los_roles_no_tienen_privilegios_de_rol(roles_db) -> None:
    for role in ROLES:
        row = await roles_db.fetchrow(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
            "rolbypassrls FROM pg_roles WHERE rolname = $1",
            role,
        )
        assert not any(row.values()), role
    assert not await roles_db.fetchval(
        "SELECT pg_has_role('vladimir_app', 'vladimir_migrator', 'MEMBER')"
    )


async def test_migrator_es_duenio_de_esquema_tablas_y_funciones(roles_db) -> None:
    owners = {
        r["tableowner"]
        for r in await roles_db.fetch(
            "SELECT tableowner FROM pg_tables WHERE schemaname = 'public'"
        )
    }
    assert owners == {"vladimir_migrator"}
    schema_owner = await roles_db.fetchval(
        "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'public'"
    )
    assert schema_owner == "vladimir_migrator"
    fn_owners = {
        r["owner"]
        for r in await roles_db.fetch(
            "SELECT pg_get_userbyid(p.proowner) AS owner FROM pg_proc p "
            "WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f' "
            "AND NOT EXISTS (SELECT 1 FROM pg_depend d "
            "WHERE d.objid = p.oid AND d.deptype = 'e')"
        )
    }
    assert fn_owners == {"vladimir_migrator"}


async def test_app_nunca_tiene_delete_ni_truncate(roles_db) -> None:
    tables = [
        r["tablename"]
        for r in await roles_db.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
    ]
    for table in tables:
        for privilege in ("DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            assert not await roles_db.fetchval(
                "SELECT has_table_privilege('vladimir_app', $1, $2)",
                f"public.{table}",
                privilege,
            ), (table, privilege)


async def test_app_opera_las_tablas_normales(roles_db) -> None:
    code = f"roles-{uuid4().hex[:12]}"
    await roles_db.execute("SET ROLE vladimir_app")
    try:
        # El INSERT dispara fn_log_activity, que escribe en activity_events.
        unit_id = await roles_db.fetchval(
            "INSERT INTO units (code, symbol, name) VALUES ($1, 'x', 'Prueba') "
            "RETURNING id",
            code,
        )
        await roles_db.execute("UPDATE units SET name = 'Otro' WHERE id = $1", unit_id)
        await roles_db.execute(
            "UPDATE units SET is_active = false WHERE id = $1", unit_id
        )
        assert (
            await roles_db.fetchval(
                "SELECT count(*) FROM activity_events WHERE entity_id = $1", unit_id
            )
            == 2
        )
    finally:
        await roles_db.execute("RESET ROLE")
    # Nada se borra: DELETE no esta concedido (y el trigger VLD01 lo bloquearia).
    delete = f"DELETE FROM units WHERE id = '{unit_id}'"
    assert await _sqlstate(roles_db, "vladimir_app", delete) == INSUFFICIENT_PRIVILEGE


async def test_migrator_hace_ddl_y_app_usa_secuencias_tras_reaplicar(
    roles_db,
) -> None:
    create = "CREATE TABLE tabla_serial (id serial PRIMARY KEY, v text)"
    assert await _sqlstate(roles_db, "vladimir_migrator", create) is None
    try:
        # Falla cerrada: la tabla nueva no es accesible hasta re-aplicar el script.
        select = "SELECT * FROM tabla_serial"
        assert (
            await _sqlstate(roles_db, "vladimir_app", select) == INSUFFICIENT_PRIVILEGE
        )
        await roles_db.execute(SCRIPT)
        # La columna serial exige USAGE en la secuencia.
        insert = "INSERT INTO tabla_serial (v) VALUES ('x')"
        assert await _sqlstate(roles_db, "vladimir_app", insert) is None
        update = "UPDATE tabla_serial SET v = 'y'"
        assert await _sqlstate(roles_db, "vladimir_app", update) is None
    finally:
        drop = "DROP TABLE tabla_serial"
        assert await _sqlstate(roles_db, "vladimir_migrator", drop) is None


async def test_historiales_append_only_solo_select_e_insert(roles_db) -> None:
    key = f"roles.{uuid4().hex[:8]}"
    await roles_db.execute("SET ROLE vladimir_app")
    try:
        await roles_db.execute(
            "INSERT INTO settings (key, value, value_type, default_value, "
            "group_name, description) VALUES ($1, '5'::jsonb, 'int', '5'::jsonb, "
            "'g', 'd')",
            key,
        )
        await roles_db.execute(
            "UPDATE settings SET value = '6'::jsonb, version = 2 WHERE key = $1", key
        )
        await roles_db.execute(
            "INSERT INTO settings_history (setting_key, old_value, new_value, "
            "version_after, reason) VALUES ($1, '5'::jsonb, '6'::jsonb, 2, 'prueba')",
            key,
        )
        assert await roles_db.fetchval(
            "SELECT count(*) FROM settings_history WHERE setting_key = $1", key
        )
        assert await roles_db.fetchval("SELECT count(*) FROM activity_events") >= 0
    finally:
        await roles_db.execute("RESET ROLE")
    for table in APPEND_ONLY:
        for sql in (
            f"UPDATE {table} SET id = id",
            f"DELETE FROM {table}",
            f"TRUNCATE {table}",
            f"ALTER TABLE {table} DISABLE TRIGGER ALL",
            f"DROP TABLE {table}",
        ):
            state = await _sqlstate(roles_db, "vladimir_app", sql)
            assert state == INSUFFICIENT_PRIVILEGE, sql
    for sql in ("DELETE FROM settings", "TRUNCATE settings"):
        state = await _sqlstate(roles_db, "vladimir_app", sql)
        assert state == INSUFFICIENT_PRIVILEGE, sql


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE units",
        "ALTER TABLE units ADD COLUMN x int",
        "TRUNCATE units",
        "CREATE TABLE intruso (id int)",
        "DROP SCHEMA public CASCADE",
        "CREATE INDEX ix_intruso ON units (symbol)",
        "DROP FUNCTION fn_forbid_delete() CASCADE",
        "ALTER TABLE units DISABLE TRIGGER ALL",
        "SELECT * FROM alembic_version",
        "UPDATE alembic_version SET version_num = 'x'",
        "CREATE ROLE intruso",
    ],
)
async def test_app_no_puede_ddl_ni_truncate(roles_db, sql: str) -> None:
    assert await _sqlstate(roles_db, "vladimir_app", sql) == INSUFFICIENT_PRIVILEGE
