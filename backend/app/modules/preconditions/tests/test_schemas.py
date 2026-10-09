"""Los limites y enums de los schemas de `preconditions` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.preconditions.models import (
    CATEGORY_VALUES,
    DURATION_UNIT_VALUES,
    KIND_VALUES,
    Precondition,
)
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionRead,
    PreconditionUpdate,
)


@pytest.mark.parametrize(
    "schema", [PreconditionCreate, PreconditionItemCreate, PreconditionUpdate]
)
def test_schema_matches_model(schema: type) -> None:
    assert schema_model_mismatches(schema, Precondition) == []


@pytest.mark.parametrize("schema", [PreconditionCreate, PreconditionUpdate])
def test_enums_match_checks(schema: type) -> None:
    assert enum_values(schema, "category") == CATEGORY_VALUES
    assert enum_values(schema, "duration_unit") == DURATION_UNIT_VALUES


def test_kind_is_enum_in_read() -> None:
    assert enum_values(PreconditionRead, "kind") == KIND_VALUES
