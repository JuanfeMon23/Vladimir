"""Tests de los elementos de validacion del nucleo: `VersionStatus`,
`DuplicateValueError` / `CodeConflictError`."""

from typing import get_args

from app.core.db.mixins import VersionMixin
from app.core.exceptions import CodeConflictError, DuplicateValueError
from app.core.versioning import VersionStatus


def test_version_status_matches_db_check() -> None:
    check_sql = str(VersionMixin.status_check().sqltext)
    for value in get_args(VersionStatus):
        assert f"'{value}'" in check_sql
    assert check_sql.count("'") == 2 * len(get_args(VersionStatus))


def test_duplicate_value_error_message_and_details() -> None:
    error = DuplicateValueError(
        entity="personal",
        field="document_number",
        field_label="el número de documento",
        value="123",
    )
    assert error.message == "Ya existe personal con el número de documento «123»."
    assert error.details == {"document_number": "123"}


def test_code_conflict_error_with_scope_keeps_technical_keys() -> None:
    error = CodeConflictError(
        "una opción",
        "POS",
        scope=" en este conjunto",
        extra_details={"option_set_id": "abc"},
    )
    assert error.message == "Ya existe una opción con el código «POS» en este conjunto."
    assert error.details == {"option_set_id": "abc", "code": "POS"}
