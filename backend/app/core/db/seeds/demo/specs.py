"""Tipos de los datos de demostracion (solo datos, sin I/O).

Los modulos de datos (`staff.py`, `lab_areas.py`, `result_templates/*.py`...)
declaran constantes con estos tipos; los `load` de cada uno las envian a la
API. Separar datos y carga permite validar la estructura del dataset en
memoria (`tests/test_demo_dataset.py`) sin tocar ninguna BD.
"""

from dataclasses import dataclass, field
from typing import Literal

ResultType = Literal[
    "numeric",
    "boolean",
    "qualitative",
    "semi_quantitative",
    "titer",
    "text",
    "calculated",
]
Sex = Literal["any", "male", "female"]


@dataclass(frozen=True)
class AnalyteSpec:
    """Analito del catalogo. `unit` = `code` UCUM de su unidad por defecto."""

    code: str
    name: str
    unit: str | None = None
    loinc: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class RangeSpec:
    """Rango de referencia de un analito de plantilla (adultos salvo que
    `age_*` / `condition` indiquen otra cosa). `option` = `code` de una
    opcion del conjunto del analito."""

    sex: Sex = "any"
    age_min: float | None = None
    age_max: float | None = None
    age_unit: Literal["dias", "meses", "anos"] | None = None
    condition: str | None = None
    low: float | None = None
    high: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    option: str | None = None
    boolean: bool | None = None
    text: str | None = None
    interpretation: str | None = None


@dataclass(frozen=True)
class FieldSpec:
    """Analito dentro de una version de plantilla."""

    analyte: str
    result_type: ResultType
    unit: str | None = None
    decimals: int | None = None
    option_set: str | None = None
    formula: str | None = None
    required: bool = True
    reportable: bool = True
    default: str | None = None
    ranges: tuple[RangeSpec, ...] = ()


@dataclass(frozen=True)
class SectionSpec:
    name: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True)
class TemplateSpec:
    code: str
    name: str
    description: str
    sections: tuple[SectionSpec, ...]
    report_settings: dict = field(
        default_factory=lambda: {"show_reference_ranges": True, "show_units": True}
    )

    def fields(self) -> list[FieldSpec]:
        return [f for section in self.sections for f in section.fields]


# --- atajos para escribir plantillas sin repetir la forma ---------------------


def num(
    analyte: str,
    unit: str,
    decimals: int,
    *ranges: RangeSpec,
    required: bool = True,
    reportable: bool = True,
) -> FieldSpec:
    return FieldSpec(
        analyte,
        "numeric",
        unit=unit,
        decimals=decimals,
        ranges=ranges,
        required=required,
        reportable=reportable,
    )


def calc(
    analyte: str,
    unit: str,
    decimals: int,
    formula: str,
    *ranges: RangeSpec,
    reportable: bool = True,
) -> FieldSpec:
    return FieldSpec(
        analyte,
        "calculated",
        unit=unit,
        decimals=decimals,
        formula=formula,
        ranges=ranges,
        reportable=reportable,
    )


def opt(
    analyte: str,
    option_set: str,
    *ranges: RangeSpec,
    result_type: ResultType = "qualitative",
    required: bool = True,
) -> FieldSpec:
    return FieldSpec(
        analyte,
        result_type,
        option_set=option_set,
        ranges=ranges,
        required=required,
    )


def text(
    analyte: str, *, required: bool = False, default: str | None = None
) -> FieldSpec:
    return FieldSpec(analyte, "text", required=required, default=default)


def between(low: float, high: float, **kwargs) -> RangeSpec:
    return RangeSpec(low=low, high=high, **kwargs)


def below(high: float, display: str | None = None, **kwargs) -> RangeSpec:
    return RangeSpec(high=high, text=display, **kwargs)


def above(low: float, display: str | None = None, **kwargs) -> RangeSpec:
    return RangeSpec(low=low, text=display, **kwargs)
