"""settings y settings_history: politicas operativas editables

`settings`: catalogo + valor vigente con CHECK de tipo y rango. `settings_history`:
append-only (trigger, SQLSTATE `LEO01`). El DDL lo aporta
`leo_sdk.settings_store.migration` (mismo esquema que en las demas apps).
Vladimir no tiene tabla de usuarios: `users_table=None` deja `updated_by`/
`changed_by` como UUID del usuario de Leo sin llave foranea. Sin FK de
`settings_history.setting_key` a `settings` a proposito. El downgrade elimina
ambas tablas y la funcion append-only con sus filas.

Revision ID: f7d3a9c25e18
Revises: e5b1c7a93d28
Create Date: 2026-10-23 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from leo_sdk.settings_store import migration

from app.core.db.triggers import forbid_delete_trigger_sql

# revision identifiers, used by Alembic.
revision: str = "f7d3a9c25e18"
down_revision: Union[str, Sequence[str], None] = "e5b1c7a93d28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("settings", "settings_history")


def upgrade() -> None:
    migration.upgrade(op, users_table=None)
    # Regla transversal: nada se borra (SQLSTATE VLD01) en ninguna tabla.
    for table in TABLES:
        op.execute(forbid_delete_trigger_sql(table))


def downgrade() -> None:
    # Los triggers de no-borrado caen con sus tablas (DROP TABLE).
    migration.downgrade(op, users_table=None)
    op.execute("DROP FUNCTION IF EXISTS fn_forbid_append_only_change()")
