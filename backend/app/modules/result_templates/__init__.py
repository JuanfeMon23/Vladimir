"""Interfaz publica del modulo `result_templates`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.result_templates.router import (
    analytes_router,
    result_option_sets_router,
    result_options_router,
    result_template_versions_router,
    result_templates_router,
    units_router,
)

__all__ = [
    "analytes_router",
    "result_option_sets_router",
    "result_options_router",
    "result_template_versions_router",
    "result_templates_router",
    "units_router",
]
