"""Fixtures de test del modulo `samples`: BD real local, aislada por test.
Mismo patron que `app/modules/preconditions/tests/conftest.py`.
"""

from uuid import uuid4

import pytest


def unique_code() -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"sample-{uuid4().hex[:24]}"


@pytest.fixture
def sample_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Sangre",
        "description": "Muestra de sangre venosa",
    }


@pytest.fixture
def sample_type_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Tubo tapa roja",
        "cap_color_hex": "#FF0000",
        "additive": None,
        "specimen": "suero",
        "volume_ml": 5,
        "storage_temperature": "2-8C",
        "stability_hours": 24,
        "draw_order": 1,
        "collection_instructions": "Dejar coagular 30 minutos antes de centrifugar.",
    }
