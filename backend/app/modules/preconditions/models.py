"""Modelos del modulo `preconditions`: precondiciones y sus items.

Tabla unica, jerarquica (`preconditions`): una fila con `parent_id IS NULL`
es una precondicion; una fila con `parent_id` es un item (`condition`) que
pertenece a ella. La jerarquia tiene **un solo nivel**: un item no puede
tener hijos. La BD la hace cumplir con un trigger (`fn_preconditions_depth`,
creado en la migracion) porque un CHECK de fila no puede ver el `parent_id`
del padre ni los hijos existentes; un indice/CHECK declarativo no alcanza
para esta regla.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import CatalogMixin, Timestamps, UUIDv7PK

KIND_VALUES = ("precondition", "condition")

CATEGORY_VALUES = (
    "ayuno",
    "dieta",
    "alcohol_sustancias",
    "tabaco",
    "medicamentos",
    "actividad_fisica",
    "abstinencia_sexual",
    "recoleccion_muestra",
    "horario_toma",
    "reposo",
    "higiene",
    "otro",
)

DURATION_UNIT_VALUES = ("minutos", "horas", "dias")


class Precondition(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Precondicion o item de precondicion (jerarquia de un solo nivel).

    `kind = "precondition"` cuando `parent_id IS NULL`, `kind = "condition"`
    cuando pertenece a una precondicion. La consistencia entre `kind` y
    `parent_id`, igual que el limite de un nivel, la fuerza el trigger
    `fn_preconditions_depth` (ver migracion).
    """

    __tablename__ = "preconditions"
    __table_args__ = (
        CheckConstraint(
            f"kind IN {KIND_VALUES}",
            name="kind",
        ),
        CheckConstraint(
            f"category IN {CATEGORY_VALUES}",
            name="category",
        ),
        CheckConstraint(
            f"duration_unit IS NULL OR duration_unit IN {DURATION_UNIT_VALUES}",
            name="duration_unit",
        ),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preconditions.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    duration_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    patient_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
