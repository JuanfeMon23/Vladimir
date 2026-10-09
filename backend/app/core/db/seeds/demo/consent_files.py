"""Acceso a los PDFs versionados de los documentos a firmar
(`consent_files/*.pdf` + `manifest.json`, generados por
`build_consent_pdfs.py`). Solo biblioteca estandar.
"""

import base64
import json
from pathlib import Path
from typing import TypedDict

CONSENT_FILES_DIR = Path(__file__).resolve().parent / "consent_files"
MANIFEST_PATH = CONSENT_FILES_DIR / "manifest.json"


class ManifestEntry(TypedDict):
    code: str
    name: str
    version: int
    file: str
    pdf_sha256: str
    pdf_size_bytes: int
    source_sha256: str


def load_manifest() -> dict[str, ManifestEntry]:
    """Entradas del manifest por `code` del documento."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {entry["code"]: entry for entry in data["files"]}


def pdf_bytes(code: str) -> bytes:
    return (CONSENT_FILES_DIR / load_manifest()[code]["file"]).read_bytes()


def pdf_base64(code: str) -> str:
    """El PDF en base64 estricto, listo para `file_base64`."""
    return base64.b64encode(pdf_bytes(code)).decode("ascii")
