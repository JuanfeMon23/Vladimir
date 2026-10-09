"""Mixins reutilizables para los modelos de todos los modulos.

Cualquier bloque de columnas que se repita en 2+ tablas vive aca, no en el
`models.py` de un modulo. Ver AGENTS.md (seccion "Convenciones") y la nota
de bóveda `Base de datos` / `Versionado` para el porque de cada patron.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class UUIDv7PK:
    """PK `id uuid` generada con `uuidv7()`, nativa de PostgreSQL 18.

    Tambien en las tablas intermedias (`lab_test_*`): desde 2026-10-02 llevan
    PK sustituta y la pareja pasa a `UniqueConstraint`, para poder desactivar
    y reactivar la misma fila (nada se borra).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )


class Timestamps:
    """Auditoria `created_at` / `updated_at` presente en toda tabla."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ActivatableMixin:
    """`is_active`: nada se elimina fisicamente, solo se desactiva.

    Toda tabla con este mixin necesita en su migracion el trigger de
    actividad (`core/db/triggers.py`), que registra cada (des)activacion en
    `activity_events`.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )


class CatalogMixin(ActivatableMixin):
    """`code` (clave de negocio, unica) + `is_active` (de `ActivatableMixin`).

    El nombre de la restriccion unica sale de `NAMING_CONVENTION`
    (`uq_<table>_code`).
    """

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class VersionMixin:
    """Columnas comunes de las tablas `<x>_versions`.

    Ciclo de vida (`draft` -> `published` -> `retired`) y reglas completas en
    la nota de bóveda `Versionado`. Este mixin solo aporta las columnas
    comunes; cada modelo concreto arma su propio `__table_args__` con:
    - `VersionMixin.status_check()`, el CHECK de `status`.
    - `UniqueConstraint("<x>_id", "version_number")`.
    - Indice unico parcial `("<x>_id")` `WHERE status = 'draft'` (un solo
      borrador por entidad), porque el nombre de la columna FK cambia segun
      la tabla (`print_label_id`, `result_template_id`, etc.).
    """

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'draft'"), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @staticmethod
    def status_check() -> CheckConstraint:
        """CHECK de `status`, para incluir en el `__table_args__` del modelo."""
        return CheckConstraint(
            "status IN ('draft', 'published', 'retired')", name="status"
        )
