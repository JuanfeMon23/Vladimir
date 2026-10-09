"""Utilidad de test reusable: compara los limites de un schema Pydantic de
entrada con las columnas de su modelo SQLAlchemy.

Generica (no importa ningun modulo): cada modulo la invoca desde su propio
`tests/test_schemas.py` con sus parejas `(schema, modelo)`. Asi el
`Field(max_length=...)` y los enums `Literal[...]` de los schemas no se
desincronizan de `models.py` (fuente de verdad de longitudes y CHECK).
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import String


def _properties(schema: type[BaseModel]) -> dict[str, Any]:
    """`properties` del JSON Schema; los modelos recursivos (p. ej.
    `PreconditionRead.items`) salen como `$ref` a `$defs`."""
    json_schema = schema.model_json_schema(mode="validation")
    if "properties" not in json_schema:
        json_schema = json_schema["$defs"][schema.__name__]
    return json_schema["properties"]


def _property_variants(prop: dict[str, Any]) -> list[dict[str, Any]]:
    """Variantes no nulas de una propiedad del JSON Schema (`anyOf` de un
    campo opcional, o la propiedad misma)."""
    variants = prop.get("anyOf", [prop])
    return [v for v in variants if v.get("type") != "null"]


def schema_model_mismatches(schema: type[BaseModel], model: type) -> list[str]:
    """Lista de discrepancias entre `schema` y las columnas `String(n)` de
    `model` con el mismo nombre. Vacia = sincronizados.

    - Campo de texto libre: su `maxLength` debe ser igual a `n`.
    - Campo enum (`Literal[...]`): cada valor debe caber en `n` (la lista de
      valores se valida aparte contra el CHECK, ver `enum_values`).
    """
    columns = model.__table__.columns  # type: ignore[attr-defined]
    properties = _properties(schema)
    problems: list[str] = []
    for name, prop in properties.items():
        column = columns.get(name)
        if column is None or not isinstance(column.type, String):
            continue
        length = column.type.length
        if length is None:  # Text: sin limite
            continue
        for variant in _property_variants(prop):
            if "enum" in variant:
                too_long = [v for v in variant["enum"] if len(v) > length]
                if too_long:
                    problems.append(f"{schema.__name__}.{name}: {too_long} > {length}")
            elif variant.get("type") == "string":
                actual = variant.get("maxLength")
                if actual != length:
                    problems.append(
                        f"{schema.__name__}.{name}: maxLength={actual}, BD={length}"
                    )
    return problems


def enum_values(schema: type[BaseModel], field: str) -> tuple[str, ...]:
    """Valores del enum de `field` tal como salen en el OpenAPI."""
    prop = _properties(schema)[field]
    for variant in _property_variants(prop):
        if "enum" in variant:
            return tuple(variant["enum"])
    raise AssertionError(f"{schema.__name__}.{field} no es un enum")
