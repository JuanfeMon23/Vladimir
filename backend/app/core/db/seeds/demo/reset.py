"""Reset y conteos de la BD de desarrollo para el comando de demostracion."""

import sqlalchemy as sa

from app.core.db.base import Base
from app.core.db.seeds.result_option_sets import seed_result_option_sets
from app.core.db.seeds.units import seed_units

# Catalogos que ya trae la semilla estandar: no cuentan como "datos" al
# decidir si la BD esta vacia.
SEEDED_CATALOGS = frozenset({"units", "result_option_sets", "result_options"})


def business_tables() -> list[str]:
    """Todas las tablas del esquema (`alembic_version` no esta en `Base`)."""
    import app.core.db.registry  # noqa: F401  (registra los modelos)

    return [table.name for table in Base.metadata.sorted_tables]


def truncate_sql(tables: list[str]) -> str:
    return "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"


def row_counts(connection: sa.Connection, tables: list[str]) -> dict[str, int]:
    return {
        table: connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in tables
    }


def reset(connection: sa.Connection) -> None:
    """Vacia TODAS las tablas (incluida `activity_events`) y recarga las
    semillas de catalogo estandar. `TRUNCATE` no dispara los triggers
    `BEFORE DELETE`; `alembic_version` no se toca."""
    connection.execute(sa.text(truncate_sql(business_tables())))
    seed_catalogs(connection)


def seed_catalogs(connection: sa.Connection) -> None:
    seed_units(connection)
    seed_result_option_sets(connection)
