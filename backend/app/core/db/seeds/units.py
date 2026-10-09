"""Semilla de `units` (modulo `result_templates`): unidades de laboratorio
comunes, con codigo UCUM (https://ucum.org, case-sensitive).

A validar con el laboratorio. La migracion 98b5c90d1b86 la ejecuta antes de
convertir el texto libre de unidades a FK, para que los textos existentes
se emparejen con estas filas por `code` o `symbol`.
"""

from typing import NamedTuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert


class UnitSeed(NamedTuple):
    code: str
    symbol: str
    name: str


UNITS: tuple[UnitSeed, ...] = (
    UnitSeed("mg/dL", "mg/dL", "miligramos por decilitro"),
    UnitSeed("g/dL", "g/dL", "gramos por decilitro"),
    UnitSeed("ug/dL", "µg/dL", "microgramos por decilitro"),
    UnitSeed("ng/mL", "ng/mL", "nanogramos por mililitro"),
    UnitSeed("ng/dL", "ng/dL", "nanogramos por decilitro"),
    UnitSeed("pg/mL", "pg/mL", "picogramos por mililitro"),
    UnitSeed("umol/L", "µmol/L", "micromoles por litro"),
    UnitSeed("mmol/L", "mmol/L", "milimoles por litro"),
    UnitSeed("meq/L", "mEq/L", "miliequivalentes por litro"),
    UnitSeed("U/L", "U/L", "unidades por litro"),
    UnitSeed("m[IU]/mL", "mUI/mL", "miliunidades internacionales por mililitro"),
    UnitSeed("[IU]/mL", "UI/mL", "unidades internacionales por mililitro"),
    UnitSeed("[IU]/L", "UI/L", "unidades internacionales por litro"),
    UnitSeed("%", "%", "porcentaje"),
    UnitSeed("fL", "fL", "femtolitros"),
    UnitSeed("pg", "pg", "picogramos"),
    UnitSeed("10*3/uL", "×10³/µL", "miles por microlitro"),
    UnitSeed("10*6/uL", "×10⁶/µL", "millones por microlitro"),
    UnitSeed("mg/L", "mg/L", "miligramos por litro"),
    UnitSeed("g/L", "g/L", "gramos por litro"),
    UnitSeed(
        "mL/min/{1.73_m2}",
        "mL/min/1,73 m²",
        "mililitros por minuto por 1,73 m² de superficie corporal",
    ),
    UnitSeed("s", "s", "segundos"),
    UnitSeed("min", "min", "minutos"),
    UnitSeed("mm/h", "mm/h", "milímetros por hora"),
    UnitSeed("mg/(24.h)", "mg/24 h", "miligramos en 24 horas"),
    UnitSeed("[pH]", "pH", "unidades de pH"),
    UnitSeed("{ratio}", "razón", "razón (adimensional)"),
    UnitSeed("mosm/kg", "mOsm/kg", "miliosmoles por kilogramo"),
    UnitSeed("ug/L", "µg/L", "microgramos por litro"),
    UnitSeed("nmol/L", "nmol/L", "nanomoles por litro"),
)

_units = sa.table(
    "units",
    sa.column("code", sa.String),
    sa.column("symbol", sa.String),
    sa.column("name", sa.String),
)


def seed_units(connection: sa.Connection) -> None:
    """Inserta las unidades cuyo `code` aun no existe."""
    connection.execute(
        insert(_units)
        .values([unit._asdict() for unit in UNITS])
        .on_conflict_do_nothing(index_elements=["code"])
    )
