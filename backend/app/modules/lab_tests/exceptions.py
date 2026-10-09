"""Errores del modulo `lab_tests`."""

from app.core.exceptions import ValidationAppError


class LabTestSampleTypesRequiredError(ValidationAppError):
    """Un examen siempre lleva al menos un tipo de muestra (el recipiente):
    ni al crearlo ni al reemplazar su set puede quedar sin ninguno."""

    def __init__(self) -> None:
        super().__init__(
            message="El examen debe tener al menos un tipo de muestra.",
            details={"field": "sample_types"},
        )


class LabTestSampleTypePreferredCountError(ValidationAppError):
    """El body de `PUT /lab-tests/{id}/sample-types` debe traer exactamente
    un `is_preferred=true` (ver `lab_test_sample_types`: indice unico
    parcial de a lo sumo un preferido por examen, y aqui ademas se exige
    que haya uno)."""

    def __init__(self, preferred_count: int) -> None:
        super().__init__(
            message=(
                "Debe haber exactamente un tipo de muestra con "
                f"'is_preferred=true' (se recibieron {preferred_count})."
            ),
            details={"preferred_count": preferred_count},
        )
