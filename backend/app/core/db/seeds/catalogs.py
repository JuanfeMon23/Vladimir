"""Semilla de los catalogos de categoria (regla «Catalogos en BD»).

Cada lista seleccionable que antes era un `CHECK` con tupla es una tabla de
catalogo (`code` estable, `name` visible, `sort_order`, `is_active` y, si hace
falta, columnas de comportamiento). Los `code` son exactamente los valores que
tenian los CHECK: los datos existentes no cambian.

Idempotente: inserta solo los `code` que faltan (`ON CONFLICT DO NOTHING`) y
no pisa nombres, orden ni `is_active` editados desde la app. La migracion
e3a7c91b5d24 la ejecuta antes de crear las FK.

`sort_order` sale de la posicion (10, 20, 30...), para poder intercalar.
"""

from typing import Any, NamedTuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


class CatalogSeed(NamedTuple):
    table: str
    # Columnas de comportamiento, en el orden de los valores extra de `rows`.
    extra_columns: tuple[str, ...]
    # (code, name, *valores de extra_columns)
    rows: tuple[tuple[Any, ...], ...]


CATALOGS: tuple[CatalogSeed, ...] = (
    CatalogSeed(
        "consent_document_types",
        (),
        (
            ("consentimiento_informado", "Consentimiento informado de examen"),
            ("tratamiento_datos", "Tratamiento de datos (general)"),
            ("otro", "Otro"),
        ),
    ),
    CatalogSeed(
        "consent_signers",
        (),
        (
            ("paciente", "Paciente"),
            ("paciente_o_representante", "Paciente o representante"),
        ),
    ),
    # `minutes`: minutos que equivale una unidad (para comparar duraciones).
    CatalogSeed(
        "duration_units",
        ("minutes",),
        (
            ("minutos", "Minutos", 1),
            ("horas", "Horas", 60),
            ("dias", "Días", 1440),
        ),
    ),
    CatalogSeed(
        "precondition_kinds",
        (),
        (
            ("precondition", "Precondición"),
            ("condition", "Condición"),
        ),
    ),
    CatalogSeed(
        "precondition_categories",
        (),
        (
            ("ayuno", "Ayuno"),
            ("dieta", "Dieta"),
            ("alcohol_sustancias", "Alcohol y sustancias"),
            ("tabaco", "Tabaco"),
            ("medicamentos", "Medicamentos"),
            ("actividad_fisica", "Actividad física"),
            ("abstinencia_sexual", "Abstinencia sexual"),
            ("recoleccion_muestra", "Recolección de muestra"),
            ("horario_toma", "Horario de toma"),
            ("reposo", "Reposo"),
            ("higiene", "Higiene"),
            ("otro", "Otro"),
        ),
    ),
    CatalogSeed(
        "specimen_types",
        (),
        (
            ("suero", "Suero"),
            ("plasma", "Plasma"),
            ("sangre_total", "Sangre total"),
            ("orina", "Orina"),
            ("heces", "Heces"),
            ("secrecion", "Secreción"),
            ("otro", "Otro"),
        ),
    ),
    # Comportamiento por tipo de resultado, en este orden:
    # uses_option_set (elige de un conjunto de opciones), uses_numeric_range
    # (low/high/critical_*), uses_boolean_range (expected_boolean), uses_unit
    # (unidad y decimales obligatorios para publicar), uses_formula (formula
    # obligatoria), requires_reference_range (si es reportable, >= 1 rango).
    CatalogSeed(
        "result_types",
        (
            "uses_option_set",
            "uses_numeric_range",
            "uses_boolean_range",
            "uses_unit",
            "uses_formula",
            "requires_reference_range",
        ),
        (
            ("numeric", "Numérico", False, True, False, True, False, True),
            ("boolean", "Booleano", False, False, True, False, False, False),
            ("qualitative", "Cualitativo", True, False, False, False, False, False),
            (
                "semi_quantitative",
                "Semicuantitativo",
                True,
                False,
                False,
                False,
                False,
                False,
            ),
            ("titer", "Título (dilución)", True, False, False, False, False, False),
            ("text", "Texto", False, False, False, False, False, False),
            ("calculated", "Calculado", False, True, False, True, True, False),
        ),
    ),
    # `is_wildcard`: la fila "cualquiera" (`any`) del rango de referencia; el
    # solapamiento la trata como coincidente con todos los sexos. A lo sumo una.
    CatalogSeed(
        "sexes",
        ("is_wildcard",),
        (
            ("any", "Cualquiera", True),
            ("male", "Masculino", False),
            ("female", "Femenino", False),
        ),
    ),
    # `days`: dias que equivale una unidad de edad (meses = 30,4375, anos = 365,25).
    CatalogSeed(
        "age_units",
        ("days",),
        (
            ("dias", "Días", 1),
            ("meses", "Meses", 30.4375),
            ("anos", "Años", 365.25),
        ),
    ),
)


def _table(seed: CatalogSeed) -> sa.TableClause:
    return sa.table(
        seed.table,
        sa.column("code"),
        sa.column("name"),
        sa.column("sort_order"),
        *(sa.column(name) for name in seed.extra_columns),
    )


def seed_catalogs(connection: sa.Connection) -> None:
    """Inserta, en cada catalogo, los `code` que aun no existen."""
    for seed in CATALOGS:
        connection.execute(
            insert(_table(seed))
            .values(
                [
                    {
                        "code": code,
                        "name": name,
                        "sort_order": position * 10,
                        **dict(zip(seed.extra_columns, extras, strict=True)),
                    }
                    for position, (code, name, *extras) in enumerate(seed.rows, 1)
                ]
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )
