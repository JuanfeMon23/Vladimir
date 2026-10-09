"""Los limites de los schemas de `lab_areas` coinciden con `models.py`."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.lab_areas.models import LabArea
from app.modules.lab_areas.schemas import LabAreaCreate, LabAreaUpdate


@pytest.mark.parametrize("schema", [LabAreaCreate, LabAreaUpdate])
def test_schema_matches_model(schema: type) -> None:
    assert schema_model_mismatches(schema, LabArea) == []
