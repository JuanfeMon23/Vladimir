"""Los limites y enums de los schemas de `result_templates` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.result_templates.models import (
    AGE_UNIT_VALUES,
    RESULT_TYPE_VALUES,
    SEX_VALUES,
    Analyte,
    ReferenceRange,
    ResultOption,
    ResultOptionSet,
    ResultTemplate,
    ResultTemplateAnalyte,
    ResultTemplateSection,
    Unit,
)
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    AnalyteUpdate,
    ReferenceRangeCreate,
    ReferenceRangeUpdate,
    ResultOptionCreate,
    ResultOptionSetCreate,
    ResultOptionSetUpdate,
    ResultOptionUpdate,
    ResultTemplateAnalyteCreate,
    ResultTemplateAnalyteUpdate,
    ResultTemplateCreate,
    ResultTemplateSectionCreate,
    ResultTemplateSectionUpdate,
    ResultTemplateUpdate,
    UnitCreate,
    UnitUpdate,
)


@pytest.mark.parametrize(
    ("schema", "model"),
    [
        (UnitCreate, Unit),
        (UnitUpdate, Unit),
        (AnalyteCreate, Analyte),
        (AnalyteUpdate, Analyte),
        (ResultOptionSetCreate, ResultOptionSet),
        (ResultOptionSetUpdate, ResultOptionSet),
        (ResultOptionCreate, ResultOption),
        (ResultOptionUpdate, ResultOption),
        (ResultTemplateCreate, ResultTemplate),
        (ResultTemplateUpdate, ResultTemplate),
        (ResultTemplateSectionCreate, ResultTemplateSection),
        (ResultTemplateSectionUpdate, ResultTemplateSection),
        (ResultTemplateAnalyteCreate, ResultTemplateAnalyte),
        (ResultTemplateAnalyteUpdate, ResultTemplateAnalyte),
        (ReferenceRangeCreate, ReferenceRange),
        (ReferenceRangeUpdate, ReferenceRange),
    ],
)
def test_schema_matches_model(schema: type, model: type) -> None:
    assert schema_model_mismatches(schema, model) == []


@pytest.mark.parametrize(
    "schema", [ResultTemplateAnalyteCreate, ResultTemplateAnalyteUpdate]
)
def test_result_type_is_enum(schema: type) -> None:
    assert enum_values(schema, "result_type") == RESULT_TYPE_VALUES


@pytest.mark.parametrize("schema", [ReferenceRangeCreate, ReferenceRangeUpdate])
def test_reference_range_enums(schema: type) -> None:
    assert enum_values(schema, "sex") == SEX_VALUES
    assert enum_values(schema, "age_unit") == AGE_UNIT_VALUES
