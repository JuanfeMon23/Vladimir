"""PDF minimo para tests (solo tests): bytes que empiezan por `%PDF-`, validos
a efectos de la validacion de archivos de la API."""

import base64
import hashlib

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def pdf_base64(pdf: bytes = MINIMAL_PDF) -> str:
    return base64.b64encode(pdf).decode()


def pdf_sha256(pdf: bytes = MINIMAL_PDF) -> str:
    return hashlib.sha256(pdf).hexdigest()
