"""Dependencias FastAPI reusables por 2+ modulos.

Ver `backend/app/core/CATALOG.md`. Una dependencia especifica de un solo
modulo vive en su propio `dependencies.py`, no aqui.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query
from sqlalchemy import ColumnElement, Select, or_
from sqlalchemy.orm import InstrumentedAttribute

from app.core import runtime_settings
from app.core.db.search import normalized, normalized_pattern
from app.core.exceptions import ValidationAppError
from app.core.schemas import VersionStatus


@dataclass
class PaginationParams:
    """`page` / `page_size` como query params de cualquier listado paginado."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


async def pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 20,
) -> PaginationParams:
    """`?page=&page_size=`; el maximo de `page_size` es el ajuste
    `pagination.max_page_size` (leido en cada peticion). Si se excede: 422
    `validation_error` con `details={field, max}`."""
    maximum = await runtime_settings.get("pagination.max_page_size")
    if page_size > maximum:
        raise ValidationAppError(
            f"El tamaño de página máximo permitido es {maximum}.",
            {"field": "page_size", "max": maximum},
        )
    return PaginationParams(page=page, page_size=page_size)


@dataclass
class ActiveOnlyFilter:
    """Filtro `?active=true` sobre catalogos con columna `is_active`.

    `active=None` (no se envio el query param) significa "sin filtrar":
    devuelve tanto activos como inactivos.
    """

    active: bool | None = None

    def apply[StmtT: Select](
        self, stmt: StmtT, column: InstrumentedAttribute[bool]
    ) -> StmtT:
        """Agrega `WHERE <column> = :active` si se envio `?active=`; si no,
        devuelve `stmt` sin tocar. Sirve igual para el `select` de items
        que para el `select(func.count())` del total."""
        if self.active is None:
            return stmt
        return stmt.where(column == self.active)


def active_only_filter(
    active: Annotated[bool | None, Query()] = None,
) -> ActiveOnlyFilter:
    return ActiveOnlyFilter(active=active)


SEARCH_MAX_LENGTH = 100
SEARCH_MAX_TERMS = 8


@dataclass(frozen=True)
class SearchFilter:
    """Busqueda `?q=` de los listados paginados.

    Insensible a mayusculas y tildes (`unaccent(lower(col))`, sin
    indices). Multi-palabra: AND entre palabras,
    OR entre las columnas pasadas a `apply`. `%`, `_` y `\\` del texto se
    buscan literalmente. Vacio o solo espacios = sin filtro.
    """

    q: str | None = None

    @property
    def terms(self) -> list[str]:
        """Palabras del texto (espacios colapsados, maximo `SEARCH_MAX_TERMS`)."""
        return (self.q or "").split()[:SEARCH_MAX_TERMS]

    def apply[StmtT: Select](self, stmt: StmtT, *columns: ColumnElement) -> StmtT:
        """Agrega el `WHERE` de la busqueda; sin texto devuelve `stmt` igual.
        Sirve para el `select` de items y para el conteo (`paginate`)."""
        for term in self.terms:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = normalized_pattern(escaped)
            stmt = stmt.where(
                or_(*(normalized(c).like(pattern, escape="\\") for c in columns))
            )
        return stmt


NO_SEARCH = SearchFilter()
"""Sin busqueda: valor por defecto de los parametros `search` de controllers y repositories."""


def search_filter(
    q: Annotated[
        str | None,
        Query(
            max_length=SEARCH_MAX_LENGTH,
            description=(
                "Texto a buscar (sin distinguir mayúsculas ni tildes). Varias "
                "palabras: deben aparecer todas, en cualquiera de las columnas "
                "buscables del listado. Vacío = sin filtro."
            ),
        ),
    ] = None,
) -> SearchFilter:
    return SearchFilter(q=q)


def include_inactive_param(
    include_inactive: Annotated[bool, Query()] = False,
) -> bool:
    """`?include_inactive=true` en los listados de contenido (filas hijas
    que se desactivan en vez de borrarse: secciones/analitos/rangos de una
    version, colecciones de un examen). Por defecto solo activas."""
    return include_inactive


def version_status_param(
    status: Annotated[VersionStatus | None, Query()] = None,
) -> VersionStatus | None:
    """`?status=draft|published|retired` en los listados de versiones
    (etiquetas, plantillas, documentos). Sin el param = todas."""
    return status
