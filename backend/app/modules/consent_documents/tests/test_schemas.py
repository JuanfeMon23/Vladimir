"""Los limites y enums de los schemas de `consent_documents` coinciden con
`models.py`."""

import pytest

from app.core.tests.schema_checks import enum_values, schema_model_mismatches
from app.modules.consent_documents.models import (
    DOCUMENT_TYPE_VALUES,
    SIGNER_VALUES,
    ConsentDocument,
    ConsentDocumentVersion,
)
from app.modules.consent_documents.schemas import (
    ConsentDocumentCreate,
    ConsentDocumentUpdate,
    ConsentDocumentVersionCreate,
    ConsentDocumentVersionUpdate,
)


@pytest.mark.parametrize(
    ("schema", "model"),
    [
        (ConsentDocumentCreate, ConsentDocument),
        (ConsentDocumentUpdate, ConsentDocument),
        (ConsentDocumentVersionCreate, ConsentDocumentVersion),
        (ConsentDocumentVersionUpdate, ConsentDocumentVersion),
    ],
)
def test_schema_matches_model(schema: type, model: type) -> None:
    assert schema_model_mismatches(schema, model) == []


@pytest.mark.parametrize("schema", [ConsentDocumentCreate, ConsentDocumentUpdate])
def test_document_type_is_enum(schema: type) -> None:
    assert enum_values(schema, "document_type") == DOCUMENT_TYPE_VALUES


@pytest.mark.parametrize(
    "schema", [ConsentDocumentVersionCreate, ConsentDocumentVersionUpdate]
)
def test_signer_is_enum(schema: type) -> None:
    assert enum_values(schema, "signer") == SIGNER_VALUES


def test_file_base64_is_write_only_and_has_file_is_derived() -> None:
    from app.modules.consent_documents.schemas import (
        ConsentDocumentVersionRead,
        ConsentDocumentVersionWithOwnerRead,
    )

    for schema in (ConsentDocumentVersionCreate, ConsentDocumentVersionUpdate):
        assert "file_base64" in schema.model_fields
        for derived in ("file_sha256", "file_size_bytes", "file_content_type"):
            assert derived not in schema.model_fields  # nunca los envia el cliente
    for schema in (ConsentDocumentVersionRead, ConsentDocumentVersionWithOwnerRead):
        assert "file_base64" not in schema.model_fields
        assert {"file_sha256", "file_size_bytes", "file_content_type"} <= set(
            schema.model_fields
        )
        assert "has_file" in schema.model_computed_fields
