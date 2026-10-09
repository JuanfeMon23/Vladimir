"""Unidades y conjuntos de opciones que la demostracion agrega a los de la
semilla estandar (`seed_units`, `seed_result_option_sets`), creados por el
flujo normal de la API.

Unidades: codigo UCUM (https://ucum.org). Conjuntos: nominales o escalas
usadas por las plantillas (grupo sanguineo, antibiograma, sedimento...).
"""

from typing import NamedTuple


class UnitSeed(NamedTuple):
    code: str
    symbol: str
    name: str


class OptionSeed(NamedTuple):
    code: str
    label: str
    is_abnormal: bool = False


class OptionSetSeed(NamedTuple):
    code: str
    name: str
    options: tuple[OptionSeed, ...]


EXTRA_UNITS: tuple[UnitSeed, ...] = (
    UnitSeed(
        "u[IU]/mL",
        "µUI/mL",
        "microunidades internacionales por mililitro",
    ),
    UnitSeed("/[HPF]", "/campo 40x", "por campo de alto poder (40x)"),
    UnitSeed("/[LPF]", "/campo 10x", "por campo de bajo poder (10x)"),
    UnitSeed(
        "[CFU]/mL",
        "UFC/mL",
        "unidades formadoras de colonias por mililitro",
    ),
    UnitSeed("mL/(24.h)", "mL/24 h", "mililitros en 24 horas"),
)

EXTRA_OPTION_SETS: tuple[OptionSetSeed, ...] = (
    OptionSetSeed(
        "grupo_abo",
        "Grupo sanguíneo ABO",
        (
            OptionSeed("a", "Grupo A"),
            OptionSeed("b", "Grupo B"),
            OptionSeed("ab", "Grupo AB"),
            OptionSeed("o", "Grupo O"),
        ),
    ),
    OptionSetSeed(
        "factor_rh",
        "Factor Rh",
        (OptionSeed("positivo", "Rh positivo"), OptionSeed("negativo", "Rh negativo")),
    ),
    OptionSetSeed(
        "sensibilidad",
        "Sensibilidad a antibióticos",
        (
            OptionSeed("sensible", "Sensible"),
            OptionSeed("intermedio", "Intermedio"),
            OptionSeed("resistente", "Resistente", True),
        ),
    ),
    OptionSetSeed(
        "escasas_abundantes",
        "Cantidad (ausentes a abundantes)",
        (
            OptionSeed("ausentes", "Ausentes"),
            OptionSeed("escasas", "Escasas"),
            OptionSeed("moderadas", "Moderadas", True),
            OptionSeed("abundantes", "Abundantes", True),
        ),
    ),
    OptionSetSeed(
        "consistencia_heces",
        "Consistencia de las heces",
        (
            OptionSeed("formada", "Formada"),
            OptionSeed("blanda", "Blanda"),
            OptionSeed("pastosa", "Pastosa"),
            OptionSeed("dura", "Dura", True),
            OptionSeed("diarreica", "Diarreica", True),
            OptionSeed("liquida", "Líquida", True),
        ),
    ),
)
