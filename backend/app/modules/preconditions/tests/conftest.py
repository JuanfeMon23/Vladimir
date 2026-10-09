"""Fixtures de test del modulo `preconditions`: BD real local, aislada por
test. Mismo patron que `app/modules/staff/tests/conftest.py`.
"""

from uuid import uuid4

import pytest


def unique_code() -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"precond-{uuid4().hex[:24]}"


@pytest.fixture
def precondition_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Ayuno de 8 horas",
        "description": "Ayuno previo a la toma de muestra",
        "category": "ayuno",
        "duration_value": 8,
        "duration_unit": "horas",
        "patient_instructions": "No consumir alimentos ni bebidas, excepto agua.",
    }


@pytest.fixture
def precondition_item_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Suspender lacteos",
        "description": "No consumir lacteos durante el ayuno",
        "category": "dieta",
        "patient_instructions": "Evitar leche, queso y derivados.",
    }
