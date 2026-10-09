"""Documentos a firmar (version 1 publicada, con su PDF).

Solo dos: el consentimiento general de tratamiento de datos personales
(`CONSENT_DATOS`, no se enlaza a examenes: la app de firmas lo pide primero a
todo paciente) y el consentimiento informado de VIH (`CONSENT_VIH`, unico que
enlaza un examen). Sin base legal propia para otros examenes, no hay mas
documentos. Texto y PDF salen de `consent_texts.py` (fuente unica) y del
`manifest.json` que genera `build_consent_pdfs.py`. El area juridica del
laboratorio debe revisar y completar los textos antes de usarlos.
"""

from typing import NamedTuple

from app.core.db.seeds.demo import consent_files, consent_texts
from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class ConsentSeed(NamedTuple):
    code: str
    name: str
    description: str
    document_type: str
    signer: str
    content: str  # texto plano de la version (mismo de `consent_texts`)


CONSENTS: tuple[ConsentSeed, ...] = tuple(
    ConsentSeed(
        doc.code,
        doc.name,
        doc.description,
        doc.document_type,
        doc.signer,
        consent_texts.plain_text(doc),
    )
    for doc in (consent_texts.HIV, consent_texts.DATA_TREATMENT)
)
CONSENTS_BY_CODE = {consent.code: consent for consent in CONSENTS}


async def load(api: DemoApi, registry: Registry) -> None:
    for consent in CONSENTS:
        created = await api.post(
            "/consent-documents",
            {
                "code": consent.code,
                "name": consent.name,
                "description": consent.description,
                "document_type": consent.document_type,
            },
        )
        registry.consents[consent.code] = created["id"]
        version = await api.post(
            f"/consent-documents/{created['id']}/versions",
            {
                "content": consent.content,
                "signer": consent.signer,
                "change_notes": "Versión inicial.",
                "file_base64": consent_files.pdf_base64(consent.code),
            },
        )
        published = await api.post(
            f"/consent-documents/{created['id']}/versions/{version['id']}/publish"
        )
        registry.consent_versions[consent.code] = published["id"]
