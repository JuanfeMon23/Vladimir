"""Errores del modulo `result_templates`.

Las reglas genericas de transicion de estado (`draft` -> `published` ->
`retired`) ya levantan `ValidationAppError` / `ConflictError` directamente
desde `app.core.versioning`; aqui solo van los errores propios del dominio.
"""

from app.core.exceptions import (
    ConflictError,
    ValidationAppError,
)

# --------------------------------------------------------------------------
# Result templates / versions
# --------------------------------------------------------------------------


class ResultTemplateVersionIncompleteError(ValidationAppError):
    """No se puede publicar. Solo cuenta el contenido activo de la version.

    - `details.missing`: analitos incompletos para su `result_type`
      (`missing_fields`) o con rangos activos que ya no corresponden a su
      `result_type` (`incompatible_reference_range_ids`).
    - `details.inactive`: referencias a elementos desactivados
      (`{template_analyte_id, field, id}`; `field` es `analyte_id`,
      `unit_id`, `option_set_id`, `section_id` o `expected_option_id`).
    - `details.invalid_formula`: formulas invalidas
      (`{template_analyte_id, reason, message, codes}`; `reason` es `syntax`,
      `unknown_code`, `inactive_code` o `cycle`).
    """

    def __init__(
        self,
        missing: list[dict],
        inactive: list[dict],
        invalid_formula: list[dict] | None = None,
    ) -> None:
        invalid_formula = invalid_formula or []
        reasons = []
        if missing:
            reasons.append("hay analitos con campos faltantes")
        if inactive:
            reasons.append("incluye elementos desactivados")
        if invalid_formula:
            reasons.append("hay fórmulas inválidas")
        super().__init__(
            message=f"La plantilla no se puede publicar: {' y '.join(reasons)}.",
            details={
                "missing": missing,
                "inactive": inactive,
                "invalid_formula": invalid_formula,
            },
        )


class ResultTemplateAnalyteFormulaError(ValidationAppError):
    """La `formula` de un analito de plantilla no es valida. `details`:
    `{field: "formula", problems: [{reason, message, codes}]}` (`reason`:
    `syntax`, `unknown_code`, `inactive_code`, `cycle`)."""

    def __init__(self, problems: list[dict]) -> None:
        super().__init__(
            message=" ".join(p["message"] for p in problems),
            details={"field": "formula", "problems": problems},
        )


# --------------------------------------------------------------------------
# Sections / template analytes / reference ranges (solo editables en draft)
# --------------------------------------------------------------------------


class ResultTemplateAnalyteDuplicateError(ConflictError):
    """El analito ya esta activo en esta version (indice unico parcial
    `(version_id, analyte_id) WHERE is_active`)."""

    def __init__(self, analyte_id: str) -> None:
        super().__init__(
            message="El analito ya está incluido (activo) en esta versión.",
            details={"analyte_id": analyte_id},
        )


class ReferenceRangeBoundsError(ValidationAppError):
    """Limites invertidos tras combinar el PATCH con lo guardado (espejo de
    los CHECK de `reference_ranges`)."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__(
            message=f"Límites del rango inválidos: {'; '.join(errors)}.",
            details={"invalid_bounds": errors},
        )


class ReferenceRangeFieldsNotAllowedError(ValidationAppError):
    """El rango usa campos que no corresponden al `result_type` del analito
    de plantilla (p. ej. `low` en un analito `qualitative`)."""

    def __init__(self, result_type: str, fields: list[str]) -> None:
        super().__init__(
            message=(
                f"Un analito de tipo '{result_type}' no admite estos campos en "
                f"sus rangos: {', '.join(fields)}."
            ),
            details={"result_type": result_type, "not_allowed": fields},
        )


class ReferenceRangeOverlapError(ValidationAppError):
    """Dos rangos activos del mismo analito de plantilla se solapan para la
    misma combinacion de sexo, edad y condicion."""

    code = "reference_range_overlap"

    def __init__(self, overlapping_id: str) -> None:
        super().__init__(
            message=(
                "El rango se solapa con otro rango activo del mismo analito "
                "(mismo sexo, condición y edades que se cruzan)."
            ),
            details={"overlapping_id": overlapping_id},
        )
