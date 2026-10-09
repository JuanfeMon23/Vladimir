"""Errores del modulo `preconditions`."""

from app.core.exceptions import ValidationAppError


class PreconditionHierarchyError(ValidationAppError):
    """Viola la regla de "maximo un nivel" que fuerza el trigger de BD
    (`fn_preconditions_depth`): el padre indicado ya es un item, o ya tiene
    items hijos y no puede convertirse en uno.
    """

    def __init__(self, parent_id: str, db_message: str) -> None:
        super().__init__(
            message=(
                f"No se puede crear el item bajo '{parent_id}': "
                f"viola la jerarquia de un solo nivel ({db_message})."
            ),
            details={"parent_id": parent_id},
        )
