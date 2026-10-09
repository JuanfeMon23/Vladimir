"""Busqueda de texto insensible a mayusculas y tildes.

Solo requiere la extension `unaccent` (migracion 'search_support'). Sin
indices: a la escala actual (cientos de filas) un seq scan basta. Si alguna
tabla llega a miles de filas, reintroducir indices GIN trigram sobre
`f_unaccent(lower(col))` (ver la decision en el archivo del subagente).

    normalized(Model.name).like(normalized_pattern(term))
"""

from sqlalchemy import func, literal
from sqlalchemy.sql.elements import ColumnElement


def normalized(column: ColumnElement) -> ColumnElement[str]:
    """`unaccent(lower(column))`."""
    return func.unaccent(func.lower(column))


def normalized_pattern(term: str) -> ColumnElement[str]:
    """Patron de contencion normalizado: `unaccent(lower('%term%'))`.

    No escapa `%`/`_` del termino: hacerlo (si se desea) es del backend.
    """
    return func.unaccent(func.lower(literal(f"%{term}%")))
