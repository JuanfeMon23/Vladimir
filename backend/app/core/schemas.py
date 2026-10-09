"""Esquemas genericos del nucleo: paginacion y error uniforme.

Cualquier modulo que necesite paginar un listado o levantar un error
estructurado reutiliza lo de aqui; no se redefine por modulo (ver
`backend-reusable-core` / `CATALOG.md`).
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# Longitud de `code` de catalogo (`String(64)` en `core/db/mixins.py::
# CatalogMixin`). Los demas limites de texto se declaran con
# `Field(max_length=...)` en el schema de cada modulo, igual al `String(n)`
# de su `models.py` (lo verifica `core/tests/schema_checks.py`).
CODE_MAX_LENGTH = 64

CodeStr = Annotated[str, Field(max_length=CODE_MAX_LENGTH)]
"""`code` de catalogo con su longitud maxima de BD ya aplicada."""

# Mismos valores que `VersionMixin.status_check()` (core/db/mixins.py). Lo usan
# los `XVersionRead` de los modulos versionados para documentar el estado como
# enum en el OpenAPI. Vive aqui (y `core.versioning` lo reexporta) para que
# `core.dependencies` no dependa de `core.versioning`.
VersionStatus = Literal["draft", "published", "retired"]


ACTIVITY_REASON_MAX_LENGTH = 255


class ActivityReasonInput(BaseModel):
    """Mixin de los `XUpdate` (PATCH) de toda entidad con `is_active`.

    `activity_reason` es el motivo opcional de la (des)activacion que trae
    el mismo PATCH (`is_active`); se guarda en `activity_events.reason`
    tanto al desactivar como al reactivar. Si el PATCH no cambia
    `is_active`, se ignora. No es una columna de la entidad: los
    repositories lo excluyen al aplicar el PATCH (ver
    `core/repository.py::update_entity`).
    """

    activity_reason: str | None = Field(
        default=None, max_length=ACTIVITY_REASON_MAX_LENGTH
    )


class Page[T](BaseModel):
    """Respuesta paginada generica: `Page[XRead]`."""

    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    """Formato unico de error de toda la API (ver AGENTS.md seccion Errores)."""

    code: str
    message: str
    details: dict | list | str | None = None


class RequestValidationErrorResponse(BaseModel):
    """422 por cuerpo/parametros invalidos: formato por defecto de FastAPI
    (`detail: [{loc, msg, type}]`). Distinto de `ErrorResponse`, que es el 422
    de una regla de negocio (`validation_error`, `inactive_reference`...)."""

    detail: list[dict[str, Any]]


_ERROR_DESCRIPTIONS: dict[int, str] = {
    404: "No existe el recurso (`not_found`).",
    409: "Conflicto con lo existente (`conflict`: codigo duplicado, estado que no lo permite...).",
    422: (
        "Regla de negocio incumplida (`ErrorResponse`: `validation_error`, "
        "`inactive_reference`, `invalid_reference`...) o cuerpo/parametros "
        "invalidos (`RequestValidationErrorResponse`)."
    ),
}


def error_responses(
    *statuses: int, descriptions: dict[int, str] | None = None
) -> dict[int | str, dict[str, Any]]:
    """`responses=` de una ruta con los errores de negocio que puede devolver:
    `@router.patch("/{id}", responses=error_responses(404, 409, 422))`.
    `descriptions` reemplaza el texto de un status (p. ej. 409 `version_in_use`
    en `retire`). El 422 admite los dos formatos que existen hoy."""
    texts = {**_ERROR_DESCRIPTIONS, **(descriptions or {})}
    return {
        status: {
            "model": ErrorResponse | RequestValidationErrorResponse
            if status == 422
            else ErrorResponse,
            "description": texts[status],
        }
        for status in statuses
    }
