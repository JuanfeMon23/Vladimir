"""Modelos del modulo `lab_tests`: examenes de laboratorio.

Modulo central, dependiente de todos los demas: un examen (`lab_tests`)
referencia un area (`lab_areas`), opcionalmente una version de etiqueta
(`print_label_versions`) y una version de plantilla de resultados
(`result_template_versions`), y se relaciona N:M con precondiciones
(`preconditions`), tipos de muestra (`sample_types`) y versiones de
documentos a firmar (`consent_document_versions`) a traves de tres tablas
intermedias. Desde 2026-10-02 nada se borra: las intermedias llevan PK
sustituta `id` (uuidv7) + `is_active`, y la pareja pasa a `UNIQUE` para que
quitar/volver a poner una asociacion sea desactivar/reactivar la misma fila.

Regla "la version referenciada debe estar `published`"
(`print_label_version_id`, `result_template_version_id`, cada
`consent_document_version_id` en `lab_test_consent_documents`): no es un
CHECK de fila (un CHECK no puede hacer subconsultas a otra tabla en
PostgreSQL) y, a diferencia del trigger de `preconditions`
(invariante interna, de una sola tabla, sin ambiguedad), aqui el ciclo de
vida de las versiones es independiente del de `lab_tests` -- una version
puede pasar de `published` a `retired` despues de haber sido enlazada, y
decidir que pasa con el examen en ese momento (bloquear el retiro, advertir,
dejarlo vigente) es una decision de flujo de negocio, no de integridad de
esquema. Queda para el controller de `backend-fastapi`.
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import ActivatableMixin, CatalogMixin, Timestamps, UUIDv7PK

# Mismo dominio de valores que `preconditions.models.DURATION_UNIT_VALUES`;
# se redeclara aca porque `lab_test_preconditions` solo necesita el CHECK
# del override, no el resto del modulo `preconditions`.
DURATION_UNIT_VALUES = ("minutos", "horas", "dias")


class LabTest(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Examen de laboratorio (catálogo)."""

    __tablename__ = "lab_tests"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_areas.id"),
        nullable=False,
        index=True,
    )
    method: Mapped[str | None] = mapped_column(String(150), nullable=True)
    turnaround_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loinc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cups_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    print_label_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("print_label_versions.id"),
        nullable=True,
        index=True,
    )
    result_template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_template_versions.id"),
        nullable=True,
        index=True,
    )


class LabTestPrecondition(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Precondicion exigida por un examen, con overrides opcionales.

    Unico `(lab_test_id, precondition_id)`: quitar la precondicion la
    desactiva, volver a ponerla reactiva la misma fila.
    """

    __tablename__ = "lab_test_preconditions"
    __table_args__ = (
        UniqueConstraint("lab_test_id", "precondition_id"),
        CheckConstraint(
            f"duration_unit_override IS NULL OR duration_unit_override IN {DURATION_UNIT_VALUES}",
            name="duration_unit_override",
        ),
    )

    lab_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False, index=True
    )
    precondition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preconditions.id"), nullable=False, index=True
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name_override: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_value_override: Mapped[float | None] = mapped_column(
        Numeric, nullable=True
    )
    duration_unit_override: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    patient_instructions_override: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )


class LabTestSampleType(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Tipo de muestra aceptado por un examen.

    Unico `(lab_test_id, sample_type_id)`. Indice unico parcial: a lo sumo
    un tipo de muestra activo con `is_preferred = true` por examen.
    """

    __tablename__ = "lab_test_sample_types"
    __table_args__ = (
        UniqueConstraint("lab_test_id", "sample_type_id"),
        Index(
            "uq_lab_test_sample_types_lab_test_id_preferred",
            "lab_test_id",
            unique=True,
            postgresql_where=text("is_preferred AND is_active"),
        ),
    )

    lab_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False, index=True
    )
    sample_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sample_types.id"), nullable=False, index=True
    )
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    required_volume_ml: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class LabTestConsentDocument(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Documento a firmar exigido por un examen (version concreta).

    Unico `(lab_test_id, consent_document_version_id)`.
    """

    __tablename__ = "lab_test_consent_documents"
    __table_args__ = (UniqueConstraint("lab_test_id", "consent_document_version_id"),)

    lab_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False, index=True
    )
    consent_document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consent_document_versions.id"),
        nullable=False,
        index=True,
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
