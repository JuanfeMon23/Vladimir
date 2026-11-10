"""Los limites y enums de los schemas de `result_templates` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.result_templates.models import (
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
