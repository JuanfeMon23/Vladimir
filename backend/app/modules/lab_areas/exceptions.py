"""Errores del modulo `lab_areas`."""

from app.core.exceptions import (
    ConflictError,
    ValidationAppError,
)


class ManagerAssignmentConflictError(ConflictError):
    """Ya se asigno un encargado vigente para esta area (condicion de carrera).

    El indice unico parcial `(area_id) WHERE end_at IS NULL` es la red de
    seguridad; si dos requests concurrentes intentan asignar encargado al
    mismo tiempo, una de las dos viola el indice y se traduce a este error.
    """

    def __init__(self, area_id: str) -> None:
        super().__init__(
            message="Ya existe un encargado vigente para esta área.",
            details={"area_id": area_id},
        )


class StaffNotEligibleForManagerError(ValidationAppError):
    """El `staff_id` indicado no existe o no esta activo."""

    def __init__(self, staff_id: str) -> None:
        super().__init__(
            message=(
                f"El personal con id '{staff_id}' no existe o no esta activo; "
                "no puede ser encargado de area."
            ),
            details={"staff_id": staff_id},
        )
