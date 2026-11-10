"""Los limites de los schemas de `catalogs` coinciden con las columnas de los
modelos de catalogo (`name`, `code`...)."""

import pytest

from app.core.tests.schema_checks import schema_model_mismatches
from app.modules.catalogs import CATALOGS


@pytest.mark.parametrize("spec", CATALOGS, ids=lambda spec: spec.slug)
def test_schema_matches_model(spec) -> None:
    assert schema_model_mismatches(spec.create, spec.model) == []
    assert schema_model_mismatches(spec.update, spec.model) == []


@pytest.mark.parametrize("spec", CATALOGS, ids=lambda spec: spec.slug)
def test_read_schema_exposes_every_model_column(spec) -> None:
    columns = {
        column.name
        for column in spec.model.__table__.columns  # type: ignore[attr-defined]
    }

    assert columns == set(spec.read.model_fields)
