"""Los limites y enums de los schemas de `preconditions` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.preconditions.models import (
    Precondition,
)
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionUpdate,
)


@pytest.mark.parametrize(
    "schema", [PreconditionCreate, PreconditionItemCreate, PreconditionUpdate]
)
def test_schema_matches_model(schema: type) -> None:
    assert schema_model_mismatches(schema, Precondition) == []
