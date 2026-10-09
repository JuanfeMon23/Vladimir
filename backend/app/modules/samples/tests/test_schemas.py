"""Los limites y enums de los schemas de `samples` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.samples.models import SPECIMEN_VALUES, Sample, SampleType
from app.modules.samples.schemas import (
    SampleCreate,
    SampleTypeCreate,
    SampleTypeUpdate,
    SampleUpdate,
)


@pytest.mark.parametrize(
    ("schema", "model"),
    [
        (SampleCreate, Sample),
        (SampleUpdate, Sample),
        (SampleTypeCreate, SampleType),
        (SampleTypeUpdate, SampleType),
    ],
)
def test_schema_matches_model(schema: type, model: type) -> None:
    assert schema_model_mismatches(schema, model) == []


@pytest.mark.parametrize("schema", [SampleTypeCreate, SampleTypeUpdate])
def test_specimen_is_enum(schema: type) -> None:
    assert enum_values(schema, "specimen") == SPECIMEN_VALUES
