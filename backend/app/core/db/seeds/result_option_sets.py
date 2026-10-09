"""Semilla de `result_option_sets` / `result_options` (modulo
`result_templates`), definida en la nota "Conjuntos de opciones de
resultado". A validar con el laboratorio.

Idempotente: inserta el conjunto si su `code` no existe y, dentro de cada
conjunto, las opciones cuyo `(option_set_id, code)` falte. No pisa
etiquetas ni banderas editadas.

`titulos` (resultados tipo `titer`): ninguna dilucion se marca anormal; el
umbral de positividad (p. ej. desde que dilucion) lo define el laboratorio.
Codigos de dilucion ASCII: `1_2`, `1_4`, ..., `gt_1_1024` para ">1:1024".
Uroanalisis: `color_orina` y `aspecto_orina` (nominales, sin escala).
"""

from typing import NamedTuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


class OptionSeed(NamedTuple):
    code: str
    label: str
    is_abnormal: bool = False


class OptionSetSeed(NamedTuple):
    code: str
    name: str
    options: tuple[OptionSeed, ...]


RESULT_OPTION_SETS: tuple[OptionSetSeed, ...] = (
    OptionSetSeed(
        "reactividad",
        "Reactividad",
        (
            OptionSeed("no_reactivo", "No reactivo"),
            OptionSeed("reactivo", "Reactivo", True),
            OptionSeed("indeterminado", "Indeterminado", True),
        ),
    ),
    OptionSetSeed(
        "positividad",
        "Positividad",
        (
            OptionSeed("negativo", "Negativo"),
            OptionSeed("positivo", "Positivo", True),
        ),
    ),
    OptionSetSeed(
        "cruces",
        "Cruces",
        (
            OptionSeed("negativo", "Negativo"),
            OptionSeed("trazas", "Trazas"),
            OptionSeed("1+", "+", True),
            OptionSeed("2+", "++", True),
            OptionSeed("3+", "+++", True),
            OptionSeed("4+", "++++", True),
        ),
    ),
    OptionSetSeed(
        "presencia",
        "Presencia",
        (
            OptionSeed("ausente", "Ausente"),
            OptionSeed("presente", "Presente", True),
        ),
    ),
    OptionSetSeed(
        "titulos",
        "Títulos",
        (
            OptionSeed("no_reactivo", "No reactivo"),
            *(
                OptionSeed(f"1_{n}", f"1:{n}")
                for n in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
            ),
            OptionSeed("gt_1_1024", ">1:1024"),
        ),
    ),
    OptionSetSeed(
        "color_orina",
        "Color de orina",
        (
            OptionSeed("incoloro", "Incoloro"),
            OptionSeed("amarillo_claro", "Amarillo claro"),
            OptionSeed("amarillo", "Amarillo"),
            OptionSeed("amarillo_oscuro", "Amarillo oscuro"),
            OptionSeed("ambar", "Ámbar"),
            OptionSeed("naranja", "Naranja"),
            OptionSeed("rojizo", "Rojizo", True),
            OptionSeed("marron", "Marrón", True),
        ),
    ),
    OptionSetSeed(
        "aspecto_orina",
        "Aspecto de orina",
        (
            OptionSeed("transparente", "Transparente"),
            OptionSeed("ligeramente_turbio", "Ligeramente turbio"),
            OptionSeed("turbio", "Turbio", True),
        ),
    ),
)

_option_sets = sa.table(
    "result_option_sets",
    sa.column("id", sa.Uuid),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
)
_options = sa.table(
    "result_options",
    sa.column("option_set_id", sa.Uuid),
    sa.column("code", sa.String),
    sa.column("label", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("is_abnormal", sa.Boolean),
)


def seed_result_option_sets(connection: sa.Connection) -> None:
    """Inserta los conjuntos y opciones que falten (por `code`)."""
    for option_set in RESULT_OPTION_SETS:
        connection.execute(
            insert(_option_sets)
            .values(code=option_set.code, name=option_set.name)
            .on_conflict_do_nothing(index_elements=["code"])
        )
        set_id = connection.execute(
            sa.select(_option_sets.c.id).where(_option_sets.c.code == option_set.code)
        ).scalar_one()
        connection.execute(
            insert(_options)
            .values(
                [
                    {
                        "option_set_id": set_id,
                        "code": option.code,
                        "label": option.label,
                        "sort_order": sort_order,
                        "is_abnormal": option.is_abnormal,
                    }
                    for sort_order, option in enumerate(option_set.options, start=1)
                ]
            )
            .on_conflict_do_nothing(index_elements=["option_set_id", "code"])
        )
