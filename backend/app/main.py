"""Crea la app FastAPI y registra los routers de los modulos de negocio."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from leo_sdk import leo_router

from app.core.activity import activity_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.leo import auth
from app.modules.consent_documents import (
    consent_document_versions_router,
    consent_documents_router,
)
from app.modules.lab_areas import lab_areas_router
from app.modules.lab_tests import lab_tests_router, register_version_usages
from app.modules.preconditions import preconditions_router
from app.modules.print_labels import print_label_versions_router, print_labels_router
from app.modules.result_templates import (
    analytes_router,
    result_option_sets_router,
    result_options_router,
    result_template_versions_router,
    result_templates_router,
    units_router,
)
from app.modules.samples import sample_types_router, samples_router
from app.modules.staff import staff_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Falla al arrancar si algun `require_action` usa un tag sin declarar.
    # La sincronizacion con Leo NO va aqui (ver `python -m app.core.leo_sync`).
    auth.check_catalog()
    yield
    await auth.aclose()


app = FastAPI(title="Vladimir API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)
auth.install(app)  # errores de Leo con el formato {code, message, details}
app.include_router(leo_router(auth))  # /auth/login /callback /me /activity /logout

# Usos de versiones por examenes activos (bloquea su retiro, ver core.versioning).
register_version_usages()

app.include_router(activity_router, prefix="/api/v1/activity")
app.include_router(staff_router, prefix="/api/v1/staff")
app.include_router(lab_areas_router, prefix="/api/v1/lab-areas")
app.include_router(lab_tests_router, prefix="/api/v1/lab-tests")
app.include_router(preconditions_router, prefix="/api/v1/preconditions")
app.include_router(samples_router, prefix="/api/v1/samples")
app.include_router(sample_types_router, prefix="/api/v1/sample-types")
app.include_router(print_labels_router, prefix="/api/v1/print-labels")
app.include_router(print_label_versions_router, prefix="/api/v1/print-label-versions")
app.include_router(units_router, prefix="/api/v1/units")
app.include_router(analytes_router, prefix="/api/v1/analytes")
app.include_router(result_option_sets_router, prefix="/api/v1/result-option-sets")
app.include_router(result_options_router, prefix="/api/v1/result-options")
app.include_router(result_templates_router, prefix="/api/v1/result-templates")
app.include_router(
    result_template_versions_router, prefix="/api/v1/result-template-versions"
)
app.include_router(consent_documents_router, prefix="/api/v1/consent-documents")
app.include_router(
    consent_document_versions_router, prefix="/api/v1/consent-document-versions"
)
