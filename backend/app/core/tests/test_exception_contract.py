"""Contrato de los errores de "no existe" (`not_found`) y "codigo duplicado"
(`CodeConflictError`) que lanzan los controllers: status, `code`, mensaje
(byte a byte) y `details`. Fija lo que ve el frontend y la app externa; la
tabla se escribio contra las clases por modulo que esta fabrica reemplazo."""

import pytest

from app.core.exceptions import CodeConflictError, DuplicateValueError, not_found

ENTITY_ID = "11111111-1111-1111-1111-111111111111"
PARENT_ID = "22222222-2222-2222-2222-222222222222"

CASES = [
    pytest.param(
        lambda: not_found("personal", ENTITY_ID),
        404,
        "not_found",
        f"No existe personal con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="staff_not_found",
    ),
    pytest.param(
        lambda: not_found("un area", ENTITY_ID),
        404,
        "not_found",
        f"No existe un area con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="lab_area_not_found",
    ),
    pytest.param(
        lambda: not_found("una muestra", ENTITY_ID),
        404,
        "not_found",
        f"No existe una muestra con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="sample_not_found",
    ),
    pytest.param(
        lambda: not_found("un tipo de muestra", ENTITY_ID),
        404,
        "not_found",
        f"No existe un tipo de muestra con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="sample_type_not_found",
    ),
    pytest.param(
        lambda: not_found("una precondicion", ENTITY_ID),
        404,
        "not_found",
        f"No existe una precondicion con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="precondition_not_found",
    ),
    pytest.param(
        lambda: not_found("una etiqueta", ENTITY_ID),
        404,
        "not_found",
        f"No existe una etiqueta con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="print_label_not_found",
    ),
    pytest.param(
        lambda: not_found(
            "una version",
            ENTITY_ID,
            scope=f" para la etiqueta '{PARENT_ID}'",
            parent={"print_label_id": PARENT_ID},
        ),
        404,
        "not_found",
        f"No existe una version con id '{ENTITY_ID}' para la etiqueta '{PARENT_ID}'.",
        {"print_label_id": PARENT_ID, "id": ENTITY_ID},
        id="print_label_version_not_found",
    ),
    pytest.param(
        lambda: not_found("un documento", ENTITY_ID),
        404,
        "not_found",
        f"No existe un documento con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="consent_document_not_found",
    ),
    pytest.param(
        lambda: not_found(
            "una version",
            ENTITY_ID,
            scope=f" para el documento '{PARENT_ID}'",
            parent={"consent_document_id": PARENT_ID},
        ),
        404,
        "not_found",
        f"No existe una version con id '{ENTITY_ID}' para el documento '{PARENT_ID}'.",
        {"consent_document_id": PARENT_ID, "id": ENTITY_ID},
        id="consent_document_version_not_found",
    ),
    pytest.param(
        lambda: not_found("un examen", ENTITY_ID),
        404,
        "not_found",
        f"No existe un examen con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="lab_test_not_found",
    ),
    pytest.param(
        lambda: not_found("una unidad", ENTITY_ID),
        404,
        "not_found",
        f"No existe una unidad con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="unit_not_found",
    ),
    pytest.param(
        lambda: not_found("un analito", ENTITY_ID),
        404,
        "not_found",
        f"No existe un analito con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="analyte_not_found",
    ),
    pytest.param(
        lambda: not_found("un conjunto de opciones", ENTITY_ID),
        404,
        "not_found",
        f"No existe un conjunto de opciones con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="option_set_not_found",
    ),
    pytest.param(
        lambda: not_found("una opcion", ENTITY_ID),
        404,
        "not_found",
        f"No existe una opcion con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="option_not_found",
    ),
    pytest.param(
        lambda: not_found("una plantilla", ENTITY_ID),
        404,
        "not_found",
        f"No existe una plantilla con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="template_not_found",
    ),
    pytest.param(
        lambda: not_found(
            "una version",
            ENTITY_ID,
            scope=f" para la plantilla '{PARENT_ID}'",
            parent={"result_template_id": PARENT_ID},
        ),
        404,
        "not_found",
        f"No existe una version con id '{ENTITY_ID}' para la plantilla '{PARENT_ID}'.",
        {"result_template_id": PARENT_ID, "id": ENTITY_ID},
        id="template_version_not_found",
    ),
    pytest.param(
        lambda: not_found("una seccion", ENTITY_ID),
        404,
        "not_found",
        f"No existe una seccion con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="section_not_found",
    ),
    pytest.param(
        lambda: not_found("un analito de plantilla", ENTITY_ID),
        404,
        "not_found",
        f"No existe un analito de plantilla con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="template_analyte_not_found",
    ),
    pytest.param(
        lambda: not_found("un rango de referencia", ENTITY_ID),
        404,
        "not_found",
        f"No existe un rango de referencia con id '{ENTITY_ID}'.",
        {"id": ENTITY_ID},
        id="reference_range_not_found",
    ),
    pytest.param(
        lambda: DuplicateValueError(
            entity="personal",
            field="document_number",
            field_label="el número de documento",
            value="D1",
        ),
        409,
        "conflict",
        "Ya existe personal con el número de documento «D1».",
        {"document_number": "D1"},
        id="staff_document_conflict",
    ),
    pytest.param(
        lambda: CodeConflictError("un área", "C1"),
        409,
        "conflict",
        "Ya existe un área con el código «C1».",
        {"code": "C1"},
        id="lab_area_code",
    ),
    pytest.param(
        lambda: CodeConflictError("una muestra", "C1"),
        409,
        "conflict",
        "Ya existe una muestra con el código «C1».",
        {"code": "C1"},
        id="sample_code",
    ),
    pytest.param(
        lambda: CodeConflictError("un tipo de muestra", "C1"),
        409,
        "conflict",
        "Ya existe un tipo de muestra con el código «C1».",
        {"code": "C1"},
        id="sample_type_code",
    ),
    pytest.param(
        lambda: CodeConflictError("una precondición", "C1"),
        409,
        "conflict",
        "Ya existe una precondición con el código «C1».",
        {"code": "C1"},
        id="precondition_code",
    ),
    pytest.param(
        lambda: CodeConflictError("una etiqueta", "C1"),
        409,
        "conflict",
        "Ya existe una etiqueta con el código «C1».",
        {"code": "C1"},
        id="print_label_code",
    ),
    pytest.param(
        lambda: CodeConflictError("un documento", "C1"),
        409,
        "conflict",
        "Ya existe un documento con el código «C1».",
        {"code": "C1"},
        id="consent_document_code",
    ),
    pytest.param(
        lambda: CodeConflictError("un examen", "C1"),
        409,
        "conflict",
        "Ya existe un examen con el código «C1».",
        {"code": "C1"},
        id="lab_test_code",
    ),
    pytest.param(
        lambda: CodeConflictError("una unidad", "C1"),
        409,
        "conflict",
        "Ya existe una unidad con el código «C1».",
        {"code": "C1"},
        id="unit_code",
    ),
    pytest.param(
        lambda: CodeConflictError("un analito", "C1"),
        409,
        "conflict",
        "Ya existe un analito con el código «C1».",
        {"code": "C1"},
        id="analyte_code",
    ),
    pytest.param(
        lambda: CodeConflictError("un conjunto de opciones", "C1"),
        409,
        "conflict",
        "Ya existe un conjunto de opciones con el código «C1».",
        {"code": "C1"},
        id="option_set_code",
    ),
    pytest.param(
        lambda: CodeConflictError(
            "una opción",
            "C1",
            scope=" en este conjunto",
            extra_details={"option_set_id": PARENT_ID},
        ),
        409,
        "conflict",
        "Ya existe una opción con el código «C1» en este conjunto.",
        {"option_set_id": PARENT_ID, "code": "C1"},
        id="option_code",
    ),
    pytest.param(
        lambda: CodeConflictError("una plantilla", "C1"),
        409,
        "conflict",
        "Ya existe una plantilla con el código «C1».",
        {"code": "C1"},
        id="template_code",
    ),
]


@pytest.mark.parametrize(("build", "status", "code", "message", "details"), CASES)
def test_error_contract(build, status, code, message, details) -> None:
    error = build()
    assert error.status_code == status
    assert error.code == code
    assert error.message == message
    assert error.details == details
