"""Errores base y handlers globales.

Los `controller.py` de los modulos lanzan subclases de `AppError` (nunca
`HTTPException`: el controller no conoce HTTP, ver AGENTS.md). El nucleo
traduce esas excepciones a una respuesta HTTP con el formato uniforme
`ErrorResponse`.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.core.db.triggers import FORBIDDEN_OPERATION_SQLSTATE
from app.core.schemas import ErrorResponse


class AppError(Exception):
    """Excepcion base de negocio. No se lanza directamente, se subclasea."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        details: dict | list | str | None = None,
    ) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    """Recurso no encontrado."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


def not_found(
    subject: str,
    entity_id: object,
    *,
    scope: str = "",
    parent: dict | None = None,
) -> NotFoundError:
    """404 de "no existe": `No existe {subject} con id '{id}'{scope}.` y
    `details={**parent, "id": id}`.

    - `subject`: sustantivo con articulo indefinido ("un examen", "personal").
    - `scope`: complemento opcional (" para la etiqueta 'X'").
    - `parent`: claves previas de `details` (p. ej. el id del padre).
    """
    return NotFoundError(
        message=f"No existe {subject} con id '{entity_id}'{scope}.",
        details={**(parent or {}), "id": str(entity_id)},
    )


class ConflictError(AppError):
    """Conflicto con el estado actual del recurso (p. ej. clave duplicada)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class DuplicateValueError(ConflictError):
    """Valor duplicado en una clave unica de negocio (`code`,
    `document_number`, ...).

    Arma el mensaje en espanol natural para el usuario final, p. ej.
    "Ya existe un área con el código «LAB»." `details` conserva como clave el
    nombre tecnico del campo (`{"code": "LAB"}`): el frontend lo usa para
    ubicar el error junto al input correcto, no se traduce.

    - `entity`: sustantivo con articulo indefinido ("un área", "personal").
    - `field_label`: nombre legible del campo con articulo ("el código").
    - `scope`: complemento opcional al final (" en este conjunto").
    - `extra_details`: claves adicionales de `details` (p. ej. el padre).
    """

    def __init__(
        self,
        *,
        entity: str,
        field: str,
        field_label: str,
        value: str,
        scope: str = "",
        extra_details: dict | None = None,
    ) -> None:
        super().__init__(
            message=f"Ya existe {entity} con {field_label} «{value}»{scope}.",
            details={**(extra_details or {}), field: value},
        )


class CodeConflictError(DuplicateValueError):
    """Atajo de `DuplicateValueError` para el `code` de catalogo
    (`CatalogMixin`), el caso mas comun."""

    def __init__(
        self,
        entity: str,
        value: str,
        *,
        scope: str = "",
        extra_details: dict | None = None,
    ) -> None:
        super().__init__(
            entity=entity,
            field="code",
            field_label="el código",
            value=value,
            scope=scope,
            extra_details=extra_details,
        )


class ValidationAppError(AppError):
    """Regla de negocio invalida (distinta de la validacion de schema)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class InvalidReferenceError(ValidationAppError):
    """Un id del body referencia algo que no existe (o que no corresponde,
    p. ej. una seccion de otra version): 422 limpio en vez de un
    `IntegrityError` de FK.

    - `subject`: sustantivo con articulo definido ("el analito").
    - `field`: nombre tecnico del campo del body (clave de `details`).
    - `reason`: complemento del mensaje (por defecto "no existe").
    """

    code = "invalid_reference"

    def __init__(
        self, subject: str, field: str, value: object, reason: str = "no existe"
    ) -> None:
        super().__init__(
            message=f"{subject[:1].upper()}{subject[1:]} con id '{value}' {reason}.",
            details={field: str(value)},
        )


def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def _db_error_attr(exc: DBAPIError, attr: str) -> str | None:
    """Atributo del error de asyncpg envuelto por SQLAlchemy (`sqlstate`,
    `table_name`, ...)."""
    orig = exc.orig
    return getattr(orig, attr, None) or getattr(
        getattr(orig, "__cause__", None), attr, None
    )


def db_error_handler(_request: Request, exc: DBAPIError) -> JSONResponse:
    """Traduce el `RAISE` de `fn_forbid_delete` (SQLSTATE `VLD01`: nada se
    borra, solo se desactiva) a `409 delete_forbidden`. Cualquier otro error
    de BD se relanza (500, como antes)."""
    if _db_error_attr(exc, "sqlstate") != FORBIDDEN_OPERATION_SQLSTATE:
        raise exc
    body = ErrorResponse(
        code="delete_forbidden",
        message=(
            "No se puede eliminar: en Vladimir nada se elimina, se desactiva "
            "(is_active = false)."
        ),
        details={"table": _db_error_attr(exc, "table_name")},
    )
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los handlers de excepciones en la app FastAPI."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(DBAPIError, db_error_handler)
