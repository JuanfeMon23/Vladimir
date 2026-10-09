"""Interfaz publica del modulo `print_labels`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.print_labels.router import router as print_labels_router
from app.modules.print_labels.router import (
    versions_router as print_label_versions_router,
)

__all__ = ["print_label_versions_router", "print_labels_router"]
