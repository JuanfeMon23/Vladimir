"""Modelos del modulo `staff`: catálogo del personal del laboratorio."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import ActivatableMixin, Timestamps, UUIDv7PK


class Staff(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Personal del laboratorio. De aqui se eligen los encargados de area.

    No usa `CatalogMixin`: la clave de negocio es `document_number`
    (documento de identidad), no un `code` de catalogo; `is_active` sale de
    `ActivatableMixin`.
    """

    __tablename__ = "staff"
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    document_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    professional_license: Mapped[str | None] = mapped_column(String(64), nullable=True)
