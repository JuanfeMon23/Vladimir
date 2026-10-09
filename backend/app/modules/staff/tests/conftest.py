"""Fixtures de test del modulo `staff`: BD real local, aislada por test.

Cada test corre dentro de una transaccion externa que se revierte al final
(savepoint anidado para sobrevivir a los `commit()` del repository), asi no
hace falta mockear la BD ni limpiar datos a mano.
"""

from uuid import uuid4

import pytest


def unique_document_number() -> str:
    """Genera un `document_number` unico (32 chars max) para aislar los tests
    de filas preexistentes en la tabla `staff`, sin depender de que este vacia.
    """
    return uuid4().hex[:32]


@pytest.fixture
def staff_payload() -> dict:
    return {
        "document_type": "CC",
        "document_number": unique_document_number(),
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "ana.gomez@example.com",
        "phone": "3000000000",
        "job_title": "Bacterióloga",
        "professional_license": "BAC-123",
    }
