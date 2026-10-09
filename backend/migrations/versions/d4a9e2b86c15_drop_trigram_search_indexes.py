"""drop trigram search indexes, f_unaccent and pg_trgm (keep unaccent)

Revision ID: d4a9e2b86c15
Revises: c3f8a1d27b4e
Create Date: 2026-10-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4a9e2b86c15'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1d27b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Congelado en la migracion (igual que c3f8a1d27b4e).
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
    for table, columns in INDEXES.items():
        for column in columns:
            op.execute(f'DROP INDEX ix_{table}_{column}_trgm')
    op.execute('DROP FUNCTION f_unaccent(text)')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
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
