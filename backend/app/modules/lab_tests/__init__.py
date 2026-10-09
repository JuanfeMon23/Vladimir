"""Interfaz publica del modulo `lab_tests`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).

- `lab_tests_router`: rutas `/api/v1/lab-tests`.
- `register_version_usages()`: registra en `core.versioning` que examenes
  activos usan cada version de etiqueta/plantilla/documento (bloquea su
  retiro). Lo llama `app/main.py` al arrancar.
"""

from app.modules.lab_tests.controller import register_version_usages
from app.modules.lab_tests.router import router as lab_tests_router

__all__ = ["lab_tests_router", "register_version_usages"]
