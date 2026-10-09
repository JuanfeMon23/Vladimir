"""Modelos del modulo `result_templates`: plantillas de resultados.

Ocho tablas:
- Catalogos simples (no versionados): `units` (unidades de medida UCUM),
  `analytes` (analito medible), `result_option_sets` y `result_options`
  (opciones de un resultado cualitativo, p. ej. "positivo/negativo").
- Entidad versionada (mismo patron de `VersionMixin` ya validado en
  `print_labels`): `result_templates` (catálogo base) +
  `result_template_versions` (version con `report_settings` jsonb) +
  `result_template_sections` (agrupacion visual dentro de una version) +
  `result_template_analytes` (analito incluido en una version, con su tipo
  de resultado y seccion opcional).
- `reference_ranges`: rango de referencia de un `result_template_analyte`,
  segmentado por sexo/edad/condicion.

Nada se elimina: todas tienen `is_active` (incluido el contenido de los
borradores: secciones, analitos y rangos) y la BD bloquea los DELETE.
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.db.mixins import (
    ActivatableMixin,
    CatalogMixin,
    Timestamps,
    UUIDv7PK,
    VersionMixin,
)

RESULT_TYPE_VALUES = (
    "numeric",
    "boolean",
    "qualitative",
    "semi_quantitative",
    "titer",
    "text",
    "calculated",
)

SEX_VALUES = ("any", "male", "female")

AGE_UNIT_VALUES = ("dias", "meses", "anos")


class Unit(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Unidad de medida (catálogo).

    `code` es el codigo UCUM (case-sensitive, p. ej. `ug/dL`, `10*3/uL`) y es
    la clave de negocio; `symbol` es la presentacion (`µg/dL`, `×10³/µL`) y
    `name` el nombre en español.
    """

    __tablename__ = "units"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class Analyte(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Analito medible (catálogo), p. ej. "Glucosa" o "Hemoglobina"."""

    __tablename__ = "analytes"
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResultOptionSet(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Conjunto de opciones de resultado (catálogo), p. ej. "Positivo/Negativo"."""

    __tablename__ = "result_option_sets"

    name: Mapped[str] = mapped_column(String(150), nullable=False)


class ResultOption(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Opcion dentro de un `ResultOptionSet`.

    `code` es unico dentro del conjunto, no globalmente, por lo que no usa
    `CatalogMixin` (su `code` es unico a nivel de tabla completa).
    """

    __tablename__ = "result_options"
    __table_args__ = (UniqueConstraint("option_set_id", "code"),)

    option_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_option_sets.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_abnormal: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )


class ResultTemplate(CatalogMixin, UUIDv7PK, Timestamps, Base):
    """Plantilla de resultados (catálogo). El contenido versionado vive en
    `ResultTemplateVersion`."""

    __tablename__ = "result_templates"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResultTemplateVersion(VersionMixin, UUIDv7PK, Timestamps, Base):
    """Version de una plantilla de resultados.

    Unico `(result_template_id, version_number)`; indice unico parcial para
    que exista a lo sumo un `draft` por plantilla.
    """

    __tablename__ = "result_template_versions"
    __table_args__ = (
        VersionMixin.status_check(),
        UniqueConstraint("result_template_id", "version_number"),
        Index(
            "uq_result_template_versions_result_template_id_draft",
            "result_template_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    result_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_templates.id"),
        nullable=False,
        index=True,
    )
    report_settings: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ResultTemplateSection(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Agrupacion visual de analitos dentro de una version de plantilla."""

    __tablename__ = "result_template_sections"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_template_versions.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ResultTemplateAnalyte(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Analito incluido en una version de plantilla, con su tipo de
    resultado y, opcionalmente, la seccion a la que pertenece.

    Indice unico parcial: un mismo analito esta activo a lo sumo una vez por
    version (las filas desactivadas no cuentan).
    """

    __tablename__ = "result_template_analytes"
    __table_args__ = (
        CheckConstraint(
            f"result_type IN {RESULT_TYPE_VALUES}",
            name="result_type",
        ),
        Index(
            "uq_result_template_analytes_version_id_analyte_id_active",
            "version_id",
            "analyte_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_template_versions.id"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_template_sections.id"),
        nullable=True,
        index=True,
    )
    analyte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytes.id"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    result_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id"),
        nullable=True,
        index=True,
    )
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    option_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_option_sets.id"),
        nullable=True,
        index=True,
    )
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    is_reportable: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    default_value: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ReferenceRange(ActivatableMixin, UUIDv7PK, Timestamps, Base):
    """Rango de referencia de un `ResultTemplateAnalyte`, segmentado por
    sexo, edad y/o condicion en texto libre.

    CHECK de coherencia de limites (cada uno tolera NULL en cualquiera de
    sus dos extremos): `low <= high`, `critical_low <= low`,
    `high <= critical_high`, `age_min <= age_max`.
    """

    __tablename__ = "reference_ranges"
    __table_args__ = (
        CheckConstraint(f"sex IN {SEX_VALUES}", name="sex"),
        CheckConstraint(
            f"age_unit IS NULL OR age_unit IN {AGE_UNIT_VALUES}",
            name="age_unit",
        ),
        CheckConstraint(
            "low IS NULL OR high IS NULL OR low <= high", name="low_le_high"
        ),
        CheckConstraint(
            "critical_low IS NULL OR low IS NULL OR critical_low <= low",
            name="critical_low_le_low",
        ),
        CheckConstraint(
            "high IS NULL OR critical_high IS NULL OR high <= critical_high",
            name="high_le_critical_high",
        ),
        CheckConstraint(
            "age_min IS NULL OR age_max IS NULL OR age_min <= age_max",
            name="age_min_le_age_max",
        ),
    )

    template_analyte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_template_analytes.id"),
        nullable=False,
        index=True,
    )
    sex: Mapped[str] = mapped_column(String(8), nullable=False)
    age_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    age_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    age_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    critical_low: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    critical_high: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    expected_option_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("result_options.id"),
        nullable=True,
        index=True,
    )
    expected_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    display_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
