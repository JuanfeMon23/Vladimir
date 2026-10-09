"""Interfaz publica del modulo `staff`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.staff.router import router as staff_router

__all__ = ["staff_router"]
