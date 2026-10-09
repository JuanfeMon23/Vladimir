"""units catalog

Unidades de medida: de texto libre a catalogo `units` (codigo UCUM).

- `units` (CatalogMixin + `symbol` + `name`) con triggers de actividad y de
  no borrado; se carga la semilla `app.core.db.seeds.units` (necesaria para
  emparejar los textos existentes).
- `analytes.default_unit` -> `default_unit_id`, `result_template_analytes.unit`
  -> `unit_id` (FK `units`, NULL). Cada texto se empareja por `code` o
  `symbol` sin distinguir mayusculas (gana la coincidencia exacta de `code`);
  si no coincide, se crea la unidad con code = symbol = name = texto.
- Downgrade: restaura el texto desde `units.symbol` y elimina `units` (y sus
  eventos en `activity_events`).

Revision ID: 98b5c90d1b86
Revises: 6be0a4509512
Create Date: 2026-10-02 15:20:15.410931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.db.seeds.units import seed_units
from app.core.db.triggers import (
    activity_trigger_sql,
    drop_activity_trigger_sql,
    drop_forbid_delete_trigger_sql,
    forbid_delete_trigger_name,
    forbid_delete_trigger_sql,
)


# revision identifiers, used by Alembic.
revision: str = '98b5c90d1b86'
down_revision: Union[str, Sequence[str], None] = '6be0a4509512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# tabla -> (columna de texto, columna FK)
UNIT_COLUMNS = {
    "analytes": ("default_unit", "default_unit_id"),
    "result_template_analytes": ("unit", "unit_id"),
}


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'units',
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('id', sa.UUID(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_units')),
        sa.UniqueConstraint('code', name=op.f('uq_units_code')),
    )
    op.execute(activity_trigger_sql('units'))
    op.execute(forbid_delete_trigger_sql('units'))
    seed_units(op.get_bind())

    for table, (text_column, fk_column) in UNIT_COLUMNS.items():
        op.add_column(table, sa.Column(fk_column, sa.UUID(), nullable=True))
        op.create_foreign_key(
            op.f(f'fk_{table}_{fk_column}_units'), table, 'units', [fk_column], ['id']
        )
        op.create_index(op.f(f'ix_{table}_{fk_column}'), table, [fk_column], unique=False)

    # Textos sin unidad equivalente: se crean (uno por texto, sin distinguir
    # mayusculas).
    op.execute(
        """
        INSERT INTO units (code, symbol, name)
        SELECT DISTINCT ON (lower(txt)) txt, txt, txt
        FROM (
            SELECT btrim(default_unit) AS txt FROM analytes
            UNION SELECT btrim(unit) FROM result_template_analytes
        ) texts
        WHERE txt IS NOT NULL AND txt <> ''
          AND NOT EXISTS (
              SELECT 1 FROM units u
              WHERE lower(u.code) = lower(txt) OR lower(u.symbol) = lower(txt)
          )
        ORDER BY lower(txt), txt
        ON CONFLICT (code) DO NOTHING
        """
    )
    for table, (text_column, fk_column) in UNIT_COLUMNS.items():
        op.execute(
            f"""
            UPDATE {table} t SET {fk_column} = (
                SELECT u.id FROM units u
                WHERE lower(u.code) = lower(btrim(t.{text_column}))
                   OR lower(u.symbol) = lower(btrim(t.{text_column}))
                ORDER BY u.code = btrim(t.{text_column}) DESC,
                         lower(u.code) = lower(btrim(t.{text_column})) DESC,
                         u.symbol = btrim(t.{text_column}) DESC,
                         u.created_at, u.id
                LIMIT 1
            )
            WHERE t.{text_column} IS NOT NULL AND btrim(t.{text_column}) <> ''
            """
        )
        op.drop_column(table, text_column)


def downgrade() -> None:
    """Downgrade schema."""
    for table, (text_column, fk_column) in UNIT_COLUMNS.items():
        op.add_column(table, sa.Column(text_column, sa.String(length=32), nullable=True))
        op.execute(
            f"""
            UPDATE {table} t SET {text_column} = u.symbol
            FROM units u WHERE u.id = t.{fk_column}
            """
        )
        op.drop_index(op.f(f'ix_{table}_{fk_column}'), table_name=table)
        op.drop_constraint(op.f(f'fk_{table}_{fk_column}_units'), table, type_='foreignkey')
        op.drop_column(table, fk_column)

    # El historial es inmutable para la app; aqui se limpia solo el de la
    # tabla que desaparece.
    trigger = forbid_delete_trigger_name('activity_events')
    op.execute(f"ALTER TABLE activity_events DISABLE TRIGGER {trigger}")
    op.execute("DELETE FROM activity_events WHERE entity_type = 'units'")
    op.execute(f"ALTER TABLE activity_events ENABLE TRIGGER {trigger}")

    op.execute(drop_forbid_delete_trigger_sql('units'))
    op.execute(drop_activity_trigger_sql('units'))
    op.drop_table('units')
