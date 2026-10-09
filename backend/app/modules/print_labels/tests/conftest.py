"""Fixtures de test del modulo `print_labels`: BD real local, aislada por
test. Mismo patron que `app/modules/samples/tests/conftest.py`.
"""

from uuid import uuid4

import pytest


def unique_code() -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"print-label-{uuid4().hex[:24]}"


@pytest.fixture
def print_label_payload() -> dict:
    return {
        "code": unique_code(),
        "name": "Etiqueta de tubo",
        "description": "Etiqueta termica para tubo de muestra",
    }


@pytest.fixture
def print_label_version_payload() -> dict:
    return {
        "width_mm": 40,
        "height_mm": 25,
        "dpi": 203,
        "output_format": "zpl",
        "barcode_type": "code128",
        "copies": 1,
        "template_content": "^XA^FO20,20^BY2^BCN,60,Y,N,N^FD{{code}}^FS^XZ",
        "placeholders": {"code": "Codigo de la muestra"},
    }
