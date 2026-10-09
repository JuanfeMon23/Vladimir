"""search support: unaccent, pg_trgm, f_unaccent and trigram indexes

Revision ID: c3f8a1d27b4e
Revises: 98b5c90d1b86
Create Date: 2026-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1d27b4e'
down_revision: Union[str, Sequence[str], None] = '98b5c90d1b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Congelado en la migracion (no depende de cambios futuros del modulo).
INDEXES = {
    'lab_tests': ('code', 'name'),
    'analytes': ('code', 'name'),
    'staff': ('document_number', 'first_name', 'last_name'),
    'samples': ('code', 'name'),
    'sample_types': ('code', 'name'),
    'preconditions': ('code', 'name'),
}


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS unaccent')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    # Wrapper estandar: `unaccent()` es STABLE; con el diccionario calificado
    # el resultado es determinista y se puede usar en indices de expresion.
    op.execute(
        "CREATE FUNCTION f_unaccent(text) RETURNS text "
        "LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS "
        "$$ SELECT public.unaccent('public.unaccent', $1) $$"
    )
    for table, columns in INDEXES.items():
        for column in columns:
            op.execute(
                f'CREATE INDEX ix_{table}_{column}_trgm ON {table} '
                f'USING gin (f_unaccent(lower({column})) gin_trgm_ops)'
            )


def downgrade() -> None:
    """Downgrade schema."""
    for table, columns in INDEXES.items():
        for column in columns:
            op.execute(f'DROP INDEX ix_{table}_{column}_trgm')
    op.execute('DROP FUNCTION f_unaccent(text)')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS unaccent')
