"""Interfaz publica del modulo `lab_areas`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.lab_areas.router import router as lab_areas_router

__all__ = ["lab_areas_router"]
