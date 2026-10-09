"""Interfaz publica del modulo `preconditions`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.preconditions.router import router as preconditions_router

__all__ = ["preconditions_router"]
