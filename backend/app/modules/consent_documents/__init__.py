"""Interfaz publica del modulo `consent_documents`.

Otros modulos solo pueden importar lo que se expone aqui (nunca
`repository`, `models` ni `schemas` internos directamente).
"""

from app.modules.consent_documents.router import router as consent_documents_router
from app.modules.consent_documents.router import (
    versions_router as consent_document_versions_router,
)
from app.modules.consent_documents.schemas import DATA_TREATMENT_TYPE

__all__ = [
    "DATA_TREATMENT_TYPE",
    "consent_document_versions_router",
    "consent_documents_router",
]
