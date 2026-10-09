"""Los limites y enums de los schemas de `print_labels` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.print_labels.models import (
    OUTPUT_FORMAT_VALUES,
    PrintLabel,
    PrintLabelVersion,
)
from app.modules.print_labels.schemas import (
    PrintLabelCreate,
    PrintLabelUpdate,
    PrintLabelVersionCreate,
    PrintLabelVersionRead,
    PrintLabelVersionUpdate,
)


@pytest.mark.parametrize(
    ("schema", "model"),
    [
        (PrintLabelCreate, PrintLabel),
        (PrintLabelUpdate, PrintLabel),
        (PrintLabelVersionCreate, PrintLabelVersion),
        (PrintLabelVersionUpdate, PrintLabelVersion),
    ],
)
def test_schema_matches_model(schema: type, model: type) -> None:
    assert schema_model_mismatches(schema, model) == []


@pytest.mark.parametrize("schema", [PrintLabelVersionCreate, PrintLabelVersionUpdate])
def test_output_format_is_enum(schema: type) -> None:
    assert enum_values(schema, "output_format") == OUTPUT_FORMAT_VALUES


def test_version_status_is_enum() -> None:
    assert enum_values(PrintLabelVersionRead, "status") == (
        "draft",
        "published",
        "retired",
    )
