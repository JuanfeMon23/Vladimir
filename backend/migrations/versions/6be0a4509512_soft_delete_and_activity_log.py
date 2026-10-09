"""soft delete and activity log

Nada se elimina fisicamente, solo se desactiva; cada (des)activacion queda
en `activity_events`.

- `activity_events` (historial inmutable) + `fn_log_activity` (AFTER INSERT
  OR UPDATE OF is_active) en toda tabla con `is_active`.
- `fn_forbid_delete` (BEFORE DELETE, SQLSTATE `VLD01`) en toda tabla del
  esquema; en `activity_events` bloquea tambien UPDATE.
- `is_active` en `result_template_sections`, `result_template_analytes`,
  `reference_ranges` y las tres `lab_test_*`; las `lab_test_*` pasan a PK
  sustituta `id` (uuidv7) y la pareja a UNIQUE.
- Unico parcial `(version_id, analyte_id) WHERE is_active` en
  `result_template_analytes` (los duplicados previos se desactivan, se
  conserva el mas antiguo).
- El unico parcial de `is_preferred` en `lab_test_sample_types` pasa a
  `WHERE is_preferred AND is_active` (un preferido desactivado no bloquea).
- CHECK de coherencia de limites en `reference_ranges`.
- Backfill de `activity_events` para las filas existentes (antes de crear
  los triggers, para no duplicar eventos).

El downgrade elimina las filas inactivas de las tablas que ganaron
`is_active` (antes de esta revision, quitar = borrar) y deja el resto.

Revision ID: 6be0a4509512
Revises: db1a126fd56b
Create Date: 2026-10-02 15:20:13.268486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.db.triggers import (
    activity_trigger_sql,
    drop_activity_trigger_sql,
    drop_forbid_delete_trigger_sql,
    forbid_delete_trigger_sql,
)


# revision identifiers, used by Alembic.
revision: str = '6be0a4509512'
down_revision: Union[str, Sequence[str], None] = 'db1a126fd56b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Listas congeladas al esquema de esta revision (no derivar de los modelos).
PRE_EXISTING_ACTIVATABLE = (
    "staff",
    "lab_areas",
    "preconditions",
    "samples",
    "sample_types",
    "print_labels",
    "analytes",
    "result_option_sets",
    "result_options",
    "result_templates",
    "consent_documents",
    "lab_tests",
)
NEW_ACTIVATABLE = (
    "result_template_sections",
    "result_template_analytes",
    "reference_ranges",
    "lab_test_preconditions",
    "lab_test_sample_types",
    "lab_test_consent_documents",
)
ACTIVATABLE = PRE_EXISTING_ACTIVATABLE + NEW_ACTIVATABLE
WITHOUT_IS_ACTIVE = (
    "lab_area_manager_assignments",
    "print_label_versions",
    "result_template_versions",
    "consent_document_versions",
)
# tabla puente -> segunda columna de la pareja
BRIDGES = {
    "lab_test_preconditions": "precondition_id",
    "lab_test_sample_types": "sample_type_id",
    "lab_test_consent_documents": "consent_document_version_id",
}
REFERENCE_RANGE_CHECKS = {
    "low_le_high": "low IS NULL OR high IS NULL OR low <= high",
    "critical_low_le_low": "critical_low IS NULL OR low IS NULL OR critical_low <= low",
    "high_le_critical_high": "high IS NULL OR critical_high IS NULL OR high <= critical_high",
    "age_min_le_age_max": "age_min IS NULL OR age_max IS NULL OR age_min <= age_max",
}
ANALYTE_ACTIVE_INDEX = "uq_result_template_analytes_version_id_analyte_id_active"
PREFERRED_INDEX = "uq_lab_test_sample_types_lab_test_id_preferred"
APPROXIMATE_REASON = "migración: fecha aproximada"

FN_LOG_ACTIVITY = """
CREATE FUNCTION fn_log_activity() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.is_active IS NOT DISTINCT FROM OLD.is_active THEN
        RETURN NULL;
    END IF;
    INSERT INTO activity_events (entity_type, entity_id, action, reason)
    VALUES (
        TG_TABLE_NAME,
        NEW.id,
        CASE WHEN NEW.is_active THEN 'activated' ELSE 'deactivated' END,
        NULLIF(current_setting('vladimir.activity_reason', true), '')
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

FN_FORBID_DELETE = """
CREATE FUNCTION fn_forbid_delete() RETURNS trigger AS $$
BEGIN
    IF TG_TABLE_NAME = 'activity_events' THEN
        RAISE EXCEPTION 'activity_events es un historial inmutable: no se permite % sobre sus filas', TG_OP
            USING ERRCODE = 'VLD01', TABLE = TG_TABLE_NAME;
    END IF;
    RAISE EXCEPTION 'No se permite eliminar filas de %: nada se elimina, solo se desactiva (is_active = false)', TG_TABLE_NAME
        USING ERRCODE = 'VLD01', TABLE = TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'activity_events',
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.CheckConstraint("action IN ('activated', 'deactivated')", name=op.f('ck_activity_events_action')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_activity_events')),
    )
    op.create_index(
        'ix_activity_events_entity_type_entity_id_occurred_at',
        'activity_events',
        ['entity_type', 'entity_id', 'occurred_at'],
        unique=False,
    )

    for table in NEW_ACTIVATABLE:
        op.add_column(
            table,
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        )

    # lab_test_*: PK compuesta -> PK sustituta + UNIQUE de la pareja.
    for table, other in BRIDGES.items():
        op.add_column(
            table,
            sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        )
        op.drop_constraint(f'pk_{table}', table, type_='primary')
        op.create_primary_key(f'pk_{table}', table, ['id'])
        op.alter_column(table, 'lab_test_id', nullable=False)
        op.alter_column(table, other, nullable=False)
        op.create_unique_constraint(f'uq_{table}_lab_test_id', table, ['lab_test_id', other])

    # Un analito activo por version: desactivar duplicados (se conserva el
    # mas antiguo) antes del indice unico parcial.
    op.execute(
        """
        UPDATE result_template_analytes SET is_active = false, updated_at = now()
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY version_id, analyte_id ORDER BY created_at, id
                ) AS rn
                FROM result_template_analytes
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.create_index(
        ANALYTE_ACTIVE_INDEX,
        'result_template_analytes',
        ['version_id', 'analyte_id'],
        unique=True,
        postgresql_where=sa.text('is_active'),
    )

    op.drop_index(PREFERRED_INDEX, table_name='lab_test_sample_types')
    op.create_index(
        PREFERRED_INDEX,
        'lab_test_sample_types',
        ['lab_test_id'],
        unique=True,
        postgresql_where=sa.text('is_preferred AND is_active'),
    )

    for name, condition in REFERENCE_RANGE_CHECKS.items():
        op.create_check_constraint(op.f(f'ck_reference_ranges_{name}'), 'reference_ranges', condition)

    # Backfill antes de los triggers: 'activated' en created_at para toda
    # fila; 'deactivated' en updated_at (aproximado) para las inactivas.
    for table in ACTIVATABLE:
        op.execute(
            f"""
            INSERT INTO activity_events (entity_type, entity_id, action, reason, occurred_at)
            SELECT '{table}', id, 'activated', NULL, created_at FROM {table}
            ORDER BY created_at, id
            """
        )
        op.execute(
            sa.text(
                f"""
                INSERT INTO activity_events (entity_type, entity_id, action, reason, occurred_at)
                SELECT '{table}', id, 'deactivated', :reason, updated_at FROM {table}
                WHERE NOT is_active ORDER BY updated_at, id
                """
            ).bindparams(reason=APPROXIMATE_REASON)
        )

    op.execute(FN_LOG_ACTIVITY)
    op.execute(FN_FORBID_DELETE)
    for table in ACTIVATABLE:
        op.execute(activity_trigger_sql(table))
    for table in ACTIVATABLE + WITHOUT_IS_ACTIVE:
        op.execute(forbid_delete_trigger_sql(table))
    op.execute(forbid_delete_trigger_sql('activity_events', also_update=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table in ACTIVATABLE + WITHOUT_IS_ACTIVE + ('activity_events',):
        op.execute(drop_forbid_delete_trigger_sql(table))
    for table in ACTIVATABLE:
        op.execute(drop_activity_trigger_sql(table))
    op.execute("DROP FUNCTION IF EXISTS fn_forbid_delete()")
    op.execute("DROP FUNCTION IF EXISTS fn_log_activity()")

    # Antes de esta revision, quitar = borrar: lo inactivo se elimina.
    op.execute(
        """
        DELETE FROM reference_ranges
        WHERE NOT is_active
           OR template_analyte_id IN (SELECT id FROM result_template_analytes WHERE NOT is_active)
        """
    )
    op.execute(
        """
        UPDATE result_template_analytes SET section_id = NULL
        WHERE section_id IN (SELECT id FROM result_template_sections WHERE NOT is_active)
        """
    )
    op.execute("DELETE FROM result_template_analytes WHERE NOT is_active")
    op.execute("DELETE FROM result_template_sections WHERE NOT is_active")
    for table in BRIDGES:
        op.execute(f"DELETE FROM {table} WHERE NOT is_active")

    for name in REFERENCE_RANGE_CHECKS:
        op.drop_constraint(op.f(f'ck_reference_ranges_{name}'), 'reference_ranges', type_='check')
    op.drop_index(ANALYTE_ACTIVE_INDEX, table_name='result_template_analytes')
    op.drop_index(PREFERRED_INDEX, table_name='lab_test_sample_types')
    op.create_index(
        PREFERRED_INDEX,
        'lab_test_sample_types',
        ['lab_test_id'],
        unique=True,
        postgresql_where=sa.text('is_preferred'),
    )

    for table, other in BRIDGES.items():
        op.drop_constraint(f'uq_{table}_lab_test_id', table, type_='unique')
        op.drop_constraint(f'pk_{table}', table, type_='primary')
        op.create_primary_key(f'pk_{table}', table, ['lab_test_id', other])
        op.drop_column(table, 'id')

    for table in NEW_ACTIVATABLE:
        op.drop_column(table, 'is_active')

    op.drop_index('ix_activity_events_entity_type_entity_id_occurred_at', table_name='activity_events')
    op.drop_table('activity_events')
