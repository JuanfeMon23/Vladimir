"""Fixtures de los tests de BD del nucleo (`core/db`).

`session`: BD real local dentro de una transaccion externa que se revierte
al final (mismo patron que los `conftest.py` de los modulos). Sirve para
probar triggers, CHECK e indices del esquema ya migrado (`alembic upgrade
head`).
"""

from uuid import uuid4

from sqlalchemy.exc import DBAPIError


def unique_code(prefix: str) -> str:
    """`code` unico para aislar los tests de filas preexistentes."""
    return f"{prefix}-{uuid4().hex[:24]}"


def sqlstate(exc: DBAPIError) -> str | None:
    """SQLSTATE de un error de asyncpg envuelto por SQLAlchemy."""
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(
        getattr(orig, "__cause__", None), "sqlstate", None
    )
