"""category catalogs

Regla «Catalogos en BD» (2026-11-09): los `CHECK` con tupla de categorias pasan
a tablas de catalogo y la columna es FK al `code` del catalogo.

- Tablas nuevas (CategoryMixin: `code` unico, `name`, `sort_order`,
  `is_active`) con triggers de actividad y de no borrado, y semilla
  `app.core.db.seeds.catalogs` con los mismos `code` de los CHECK:
  `consent_document_types`, `consent_signers`, `duration_units` (+ `minutes`),
  `precondition_kinds`, `precondition_categories`, `specimen_types`,
  `result_types` (+ banderas de comportamiento `uses_*`/`requires_*`),
  `sexes` (+ `is_wildcard`, indice unico parcial: la fila `any` es el
  comodin) y `age_units` (+ `days`).
- Cada columna con CHECK (10) pasa a FK `-> <catalogo>.code` con indice y se
  elimina el CHECK. Los datos no cambian: los `code` son los valores previos.
- Downgrade: vuelve a los CHECK con las tuplas originales (falla si hay filas
  con `code` agregados despues a un catalogo), quita FK e indices y elimina
  las tablas (y sus eventos en `activity_events`).

Revision ID: e3a7c91b5d24
Revises: a4c8e1d27b53
Create Date: 2026-11-09 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.db.seeds.catalogs import seed_catalogs
from app.core.db.triggers import (
    activity_trigger_sql,
    drop_activity_trigger_sql,
    drop_forbid_delete_trigger_sql,
    forbid_delete_trigger_name,
    forbid_delete_trigger_sql,
)


# revision identifiers, used by Alembic.
revision: str = "e3a7c91b5d24"
down_revision: Union[str, Sequence[str], None] = "a4c8e1d27b53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bool(name: str) -> sa.Column:
    return sa.Column(
        name, sa.Boolean(), server_default=sa.text("false"), nullable=False
    )


# tabla de catalogo -> (columnas de comportamiento, CHECK extra (nombre, SQL))
CATALOGS = {
    "consent_document_types": ((), ()),
    "consent_signers": ((), ()),
    "duration_units": (
        (sa.Column("minutes", sa.Integer(), nullable=False),),
        (("minutes_positive", "minutes > 0"),),
    ),
    "precondition_kinds": ((), ()),
    "precondition_categories": ((), ()),
    "specimen_types": ((), ()),
    "result_types": (
        (
            _bool("uses_option_set"),
            _bool("uses_numeric_range"),
            _bool("uses_boolean_range"),
            _bool("uses_unit"),
            _bool("uses_formula"),
            _bool("requires_reference_range"),
        ),
        (),
    ),
    "sexes": ((_bool("is_wildcard"),), ()),
    "age_units": (
        (sa.Column("days", sa.Numeric(precision=10, scale=4), nullable=False),),
        (("days_positive", "days > 0"),),
    ),
}

# (tabla, columna, catalogo, CHECK original que se reemplaza por la FK)
CATEGORY_COLUMNS = (
    (
        "consent_documents",
        "document_type",
        "consent_document_types",
        "document_type IN ('consentimiento_informado', 'tratamiento_datos', 'otro')",
    ),
    (
        "consent_document_versions",
        "signer",
        "consent_signers",
        "signer IN ('paciente', 'paciente_o_representante')",
    ),
    (
        "preconditions",
        "kind",
        "precondition_kinds",
        "kind IN ('precondition', 'condition')",
    ),
    (
        "preconditions",
        "category",
        "precondition_categories",
        "category IN ('ayuno', 'dieta', 'alcohol_sustancias', 'tabaco', 'medicamentos', "
        "'actividad_fisica', 'abstinencia_sexual', 'recoleccion_muestra', 'horario_toma', "
        "'reposo', 'higiene', 'otro')",
    ),
    (
        "preconditions",
        "duration_unit",
        "duration_units",
        "duration_unit IS NULL OR duration_unit IN ('minutos', 'horas', 'dias')",
    ),
    (
        "lab_test_preconditions",
        "duration_unit_override",
        "duration_units",
        "duration_unit_override IS NULL OR duration_unit_override IN ('minutos', 'horas', 'dias')",
    ),
    (
        "sample_types",
        "specimen",
        "specimen_types",
        "specimen IN ('suero', 'plasma', 'sangre_total', 'orina', 'heces', 'secrecion', 'otro')",
    ),
    (
        "result_template_analytes",
        "result_type",
        "result_types",
        "result_type IN ('numeric', 'boolean', 'qualitative', 'semi_quantitative', "
        "'titer', 'text', 'calculated')",
    ),
    ("reference_ranges", "sex", "sexes", "sex IN ('any', 'male', 'female')"),
    (
        "reference_ranges",
        "age_unit",
        "age_units",
        "age_unit IS NULL OR age_unit IN ('dias', 'meses', 'anos')",
    ),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table, (extra_columns, extra_constraints) in CATALOGS.items():
        op.create_table(
            table,
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column(
                "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
            ),
            *[column.copy() for column in extra_columns],
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
            sa.Column(
                "id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            *[
                sa.CheckConstraint(sqltext, name=op.f(f'ck_{table}_{name}'))
                for name, sqltext in extra_constraints
            ],
            sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
            sa.UniqueConstraint("code", name=op.f(f"uq_{table}_code")),
        )
    op.create_index(
        "uq_sexes_one_wildcard",
        "sexes",
        ["is_wildcard"],
        unique=True,
        postgresql_where=sa.text("is_wildcard"),
    )

    # Semilla antes de los triggers (no genera eventos de actividad) y antes
    # de las FK (los datos existentes ya usan estos `code`).
    seed_catalogs(op.get_bind())
    for table in CATALOGS:
        op.execute(activity_trigger_sql(table))
        op.execute(forbid_delete_trigger_sql(table))

    for table, column, catalog, _check in CATEGORY_COLUMNS:
        op.create_foreign_key(
            op.f(f"fk_{table}_{column}_{catalog}"), table, catalog, [column], ["code"]
        )
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)
        op.drop_constraint(op.f(f"ck_{table}_{column}"), table, type_="check")


def downgrade() -> None:
    """Downgrade schema."""
    for table, column, catalog, check in CATEGORY_COLUMNS:
        op.create_check_constraint(op.f(f"ck_{table}_{column}"), table, check)
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
        op.drop_constraint(
            op.f(f"fk_{table}_{column}_{catalog}"), table, type_="foreignkey"
        )

    # El historial es inmutable para la app; aqui se limpia solo el de las
    # tablas que desaparecen.
    trigger = forbid_delete_trigger_name("activity_events")
    op.execute(f"ALTER TABLE activity_events DISABLE TRIGGER {trigger}")
    op.execute(
        "DELETE FROM activity_events WHERE entity_type IN ("
        + ", ".join(f"'{table}'" for table in CATALOGS)
        + ")"
    )
    op.execute(f"ALTER TABLE activity_events ENABLE TRIGGER {trigger}")

    op.drop_index("uq_sexes_one_wildcard", table_name="sexes")
    for table in reversed(list(CATALOGS)):
        op.execute(drop_forbid_delete_trigger_sql(table))
        op.execute(drop_activity_trigger_sql(table))
        op.drop_table(table)
