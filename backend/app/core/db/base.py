"""Base declarativa y convención de nombres compartida por todos los modulos.

Todo modulo de negocio hereda su `models.py` de `Base` para que sus tablas
queden registradas en el mismo `MetaData` y Alembic pueda generar una sola
cadena de migraciones para todo el proyecto.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres deterministas de restricciones: usados por Alembic al autogenerar
# y necesarios para poder referenciarlas explicitamente en una migracion
# (p. ej. al dropear un indice unico parcial).
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(column_0_label)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Declarative base unica para todo el esquema de Vladimir."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
