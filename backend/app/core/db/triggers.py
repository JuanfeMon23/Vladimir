"""Triggers transversales: "nada se borra, solo se desactiva" y registro de
actividad (`activity_events`).

Las funciones `fn_log_activity` y `fn_forbid_delete` se crean una sola vez
(migracion 6be0a4509512). Toda tabla nueva necesita, en su migracion:
- `forbid_delete_trigger_sql(<tabla>)` (siempre).
- `activity_trigger_sql(<tabla>)` (si tiene `is_active`).
Los tests de `core/db/tests` fallan si una tabla de `Base.metadata` no los
tiene.

Constantes que consume el backend:
- `ACTIVITY_REASON_SETTING`: el motivo de una (des)activacion se pasa con
  `SET LOCAL vladimir.activity_reason = '<motivo>'` (o
  `set_config(..., true)`) en la misma transaccion del UPDATE.
- `FORBIDDEN_OPERATION_SQLSTATE`: SQLSTATE propio del RAISE de los DELETE
  (y de UPDATE sobre `activity_events`), para mapearlo a un error de API.
"""

ACTIVITY_REASON_SETTING = "vladimir.activity_reason"
FORBIDDEN_OPERATION_SQLSTATE = "VLD01"


def activity_trigger_name(table: str) -> str:
    return f"trg_{table}_activity"


def forbid_delete_trigger_name(table: str) -> str:
    return f"trg_{table}_forbid_delete"


def activity_trigger_sql(table: str) -> str:
    return (
        f"CREATE TRIGGER {activity_trigger_name(table)} "
        f"AFTER INSERT OR UPDATE OF is_active ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION fn_log_activity()"
    )


def forbid_delete_trigger_sql(table: str, *, also_update: bool = False) -> str:
    events = "UPDATE OR DELETE" if also_update else "DELETE"
    return (
        f"CREATE TRIGGER {forbid_delete_trigger_name(table)} "
        f"BEFORE {events} ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION fn_forbid_delete()"
    )


def drop_activity_trigger_sql(table: str) -> str:
    return f"DROP TRIGGER IF EXISTS {activity_trigger_name(table)} ON {table}"


def drop_forbid_delete_trigger_sql(table: str) -> str:
    return f"DROP TRIGGER IF EXISTS {forbid_delete_trigger_name(table)} ON {table}"
