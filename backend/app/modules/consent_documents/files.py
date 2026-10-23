"""Validacion del archivo PDF (base64) de una version de documento a firmar.

Funciones puras (sin HTTP ni BD). La API es quien calcula el hash, el tamano
y el tipo de contenido a partir de los bytes decodificados: el cliente solo
envia `file_base64`.
"""

import base64
import binascii
import hashlib
from dataclasses import dataclass

from app.core.exceptions import ValidationAppError

FILE_FIELD = "file_base64"
PDF_CONTENT_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"
MIB = 1024 * 1024


@dataclass(frozen=True)
class PdfFile:
    """Metadatos calculados de un PDF valido (columnas `file_*` de la version)."""

    content_type: str
    sha256: str
    size_bytes: int


def _invalid(reason: str, message: str) -> ValidationAppError:
    return ValidationAppError(
        message=message, details={"field": FILE_FIELD, "reason": reason}
    )


def validate_pdf_base64(value: str, max_mib: int) -> PdfFile:
    """Valida `value` (base64 estricto de un PDF de hasta `max_mib` MiB; ajuste
    `files.consent_max_mib`) y calcula sus metadatos. 422 `validation_error`
    con `details={field, reason}`; `reason`: `empty`, `too_large`,
    `invalid_base64` o `not_pdf`.
    """
    max_bytes = max_mib * MIB
    too_large = f"El archivo supera el tamaño máximo de {max_mib} MB."
    if not value:
        raise _invalid("empty", "El archivo está vacío.")
    # Longitud maxima del base64 (4 caracteres por cada 3 bytes, con relleno):
    # se comprueba antes de decodificar para no gastar memoria en un cuerpo enorme.
    if len(value) > (max_bytes + 2) // 3 * 4:
        raise _invalid("too_large", too_large)
    try:
        content = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise _invalid(
            "invalid_base64", "El archivo no es base64 válido (sin prefijo ni saltos)."
        ) from None
    if not content:
        raise _invalid("empty", "El archivo está vacío.")
    if len(content) > max_bytes:
        raise _invalid("too_large", too_large)
    if not content.startswith(PDF_SIGNATURE):
        raise _invalid("not_pdf", "El archivo no es un PDF válido.")
    return PdfFile(
        content_type=PDF_CONTENT_TYPE,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )
