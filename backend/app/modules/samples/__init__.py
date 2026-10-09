"""Interfaz publica del modulo `samples`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.samples.router import router as samples_router
from app.modules.samples.router import sample_types_router

__all__ = ["sample_types_router", "samples_router"]
