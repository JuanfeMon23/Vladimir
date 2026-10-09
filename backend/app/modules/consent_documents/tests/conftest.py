"""Fixtures de test del modulo `consent_documents`: BD real local, aislada
por test. Mismo patron que `app/modules/print_labels/tests/conftest.py`.
"""

from uuid import uuid4

import pytest

from app.core.tests.pdf import pdf_base64


def unique_code() -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"consent-document-{uuid4().hex[:24]}"


@pytest.fixture
def consent_document_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Consentimiento informado general",
        "description": "Consentimiento para procedimientos de laboratorio",
        "document_type": "consentimiento_informado",
    }


@pytest.fixture
def consent_document_version_payload() -> dict:
    return {
        "content": "# Consentimiento\n\nAcepto el procedimiento descrito.",
        "signer": "paciente",
        # Publicar exige archivo.
        "file_base64": pdf_base64(),
    }
