"""Los limites de los schemas de `staff` coinciden con `models.py`."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.staff.models import Staff
from app.modules.staff.schemas import StaffCreate, StaffUpdate


@pytest.mark.parametrize("schema", [StaffCreate, StaffUpdate])
def test_schema_matches_model(schema: type) -> None:
    assert schema_model_mismatches(schema, Staff) == []
