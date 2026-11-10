"""Los limites y enums de los schemas de `lab_tests` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.lab_tests.models import (
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
