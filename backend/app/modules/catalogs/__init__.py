"""Interfaz publica del modulo `catalogs`.

Expone los catalogos de categoria (`/api/v1/catalogs/*`) que los demas modulos
referencian por FK al `code`. Otros modulos solo pueden importar lo que se
expone aqui (nunca `repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.catalogs.registry import CATALOGS
from app.modules.catalogs.router import router as catalogs_router

__all__ = ["CATALOGS", "catalogs_router"]
