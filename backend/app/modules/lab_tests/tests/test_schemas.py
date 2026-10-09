"""Los limites y enums de los schemas de `lab_tests` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.lab_tests.models import (
    DURATION_UNIT_VALUES,
    LabTest,
    LabTestPrecondition,
)
from app.modules.lab_tests.schemas import (
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestUpdate,
)


@pytest.mark.parametrize(
    ("schema", "model"),
    [
        (LabTestCreate, LabTest),
        (LabTestUpdate, LabTest),
        (LabTestPreconditionInput, LabTestPrecondition),
    ],
)
def test_schema_matches_model(schema: type, model: type) -> None:
    assert schema_model_mismatches(schema, model) == []


def test_duration_unit_override_is_enum() -> None:
    assert (
        enum_values(LabTestPreconditionInput, "duration_unit_override")
        == DURATION_UNIT_VALUES
    )
