"""Modelos del modulo `lab_areas`: areas del laboratorio y sus encargados."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import CatalogMixin, Timestamps, UUIDv7PK


class LabArea(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Area del laboratorio (catálogo)."""

    __tablename__ = "lab_areas"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class LabAreaManagerAssignment(UUIDv7PK, Timestamps, Base):
    """Historial de encargados de un area.

    El encargado vigente se deriva de la asignacion abierta
    (`end_at IS NULL`); un indice unico parcial garantiza que exista a lo
    sumo una por area. No hay columna duplicada en `lab_areas`.
    """

    __tablename__ = "lab_area_manager_assignments"
    __table_args__ = (
        Index(
            "uq_lab_area_manager_assignments_area_id_current",
            "area_id",
            unique=True,
            postgresql_where=text("end_at IS NULL"),
        ),
    )

    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_areas.id"),
        nullable=False,
        index=True,
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=False,
        index=True,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
