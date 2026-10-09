"""Transicion NO destructiva de los documentos a firmar (una vez, idempotente).

    cd backend
    uv run python -m app.core.db.seeds.demo.consent_transition --yes

Lleva una BD de desarrollo con los 4 documentos originales (VIH, VENOPUNCION,
DATOS, PSA, v1 sin archivo) al estado final del dataset: solo `CONSENT_DATOS`
(general) y `CONSENT_VIH`, ambos con PDF, y ningun examen enlazando consentimientos
salvo VIH. Todo por la API en proceso (mismas reglas que la app): nada se borra,
lo quitado se desactiva y las versiones se retiran. Una regla de la API que
rechace un paso (409/422) se reporta, no se rodea.

Pasos: (1) quita de todos los examenes VENOPUNCION, PSA y DATOS; (2) DATOS: v2
con el PDF general, publicada, y retira lo anterior; (3) VIH: v2 con su PDF,
re-enlaza los examenes a v2 y retira lo anterior; (4) VENOPUNCION y PSA: retira
sus versiones y desactiva el documento con motivo.
"""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.db.seeds.demo import consent_files
from app.core.db.seeds.demo.client import DemoApi, DemoApiError, open_api
from app.core.db.seeds.demo.consent_documents import CONSENTS_BY_CODE
from app.core.db.seeds.demo.guard import GuardError, check_target, describe_target

REMOVED_CODES = ("CONSENT_VENOPUNCION", "CONSENT_PSA")
GENERAL_CODE = "CONSENT_DATOS"
HIV_CODE = "CONSENT_VIH"
ALL_CODES = (*REMOVED_CODES, GENERAL_CODE, HIV_CODE)
DEACTIVATION_REASON = (
    "No exigido por norma; consentimiento retirado del catálogo (2026-10-09)"
)
CHANGE_NOTES = (
    "Versión con archivo PDF y texto revisado (consentimiento general y "
    "tratamiento de datos personales de salud)."
)


def plan_links(
    links: list[dict],
    *,
    remove: set[str] | frozenset[str] = frozenset(),
    replace: dict[str, str] | None = None,
) -> list[dict] | None:
    """Nuevo set de documentos de un examen para `PUT .../consent-documents`,
    o `None` si ya esta como se quiere (idempotencia). Solo mira los enlaces
    activos; conserva `is_mandatory`; no duplica una version ya enlazada."""
    replace = replace or {}
    current = [link for link in links if link["is_active"]]
    target: dict[str, bool] = {}
    for link in current:
        version_id = link["consent_document_version_id"]
        if version_id in remove:
            continue
        version_id = replace.get(version_id, version_id)
        target.setdefault(version_id, link["is_mandatory"])
    if set(target) == {link["consent_document_version_id"] for link in current}:
        return None
    return [
        {"consent_document_version_id": version_id, "is_mandatory": mandatory}
        for version_id, mandatory in target.items()
    ]


class Transition:
    def __init__(self, api: DemoApi) -> None:
        self.api = api
        self.log: list[str] = []
        self.documents: dict[str, dict] = {}  # code -> documento
        self.versions: dict[str, list[dict]] = {}  # code -> versiones
        self.code_of_version: dict[str, str] = {}  # version_id -> code

    def say(self, message: str) -> None:
        self.log.append(message)
        print(message)

    async def refresh(self) -> None:
        """Documentos y versiones actuales (incluye inactivos y retiradas)."""
        documents = await self.api.get_all("/consent-documents")
        self.documents = {d["code"]: d for d in documents if d["code"] in ALL_CODES}
        self.versions = {}
        self.code_of_version = {}
        for code, document in self.documents.items():
            versions = await self.api.get_all(
                f"/consent-documents/{document['id']}/versions"
            )
            self.versions[code] = versions
            for version in versions:
                self.code_of_version[version["id"]] = code

    def version_ids(self, codes: tuple[str, ...]) -> set[str]:
        return {v["id"] for code in codes for v in self.versions.get(code, [])}

    async def update_exams(
        self,
        *,
        remove: set[str] | frozenset[str] = frozenset(),
        replace: dict[str, str] | None = None,
        label: str,
    ) -> None:
        for test in await self.api.get_all("/lab-tests"):
            links = await self.api.get(
                f"/lab-tests/{test['id']}/consent-documents", include_inactive="true"
            )
            plan = plan_links(links, remove=remove, replace=replace)
            if plan is None:
                continue
            await self.api.put(f"/lab-tests/{test['id']}/consent-documents", plan)
            self.say(f"  examen {test['code']}: {label}")

    async def ensure_file_version(self, code: str) -> str | None:
        """Version publicada con el PDF actual del manifest (la crea si falta).
        Devuelve su id, o `None` si el documento no existe en esta BD."""
        document = self.documents.get(code)
        if document is None:
            self.say(f"  {code}: no existe en esta BD, se omite")
            return None
        sha = consent_files.load_manifest()[code]["pdf_sha256"]
        versions = self.versions[code]
        done = next(
            (
                v
                for v in versions
                if v["status"] == "published" and v["file_sha256"] == sha
            ),
            None,
        )
        if done is not None:
            self.say(f"  {code}: v{done['version_number']} ya está publicada con PDF")
            return done["id"]
        seed = CONSENTS_BY_CODE[code]
        body = {
            "content": seed.content,
            "signer": seed.signer,
            "change_notes": CHANGE_NOTES,
            "file_base64": consent_files.pdf_base64(code),
        }
        base = f"/consent-documents/{document['id']}/versions"
        draft = next((v for v in versions if v["status"] == "draft"), None)
        if draft is None:
            draft = await self.api.post(base, body)
        else:
            draft = await self.api.patch(f"{base}/{draft['id']}", body)
        published = await self.api.post(f"{base}/{draft['id']}/publish")
        self.say(f"  {code}: v{published['version_number']} publicada con PDF")
        return published["id"]

    async def retire_published(self, code: str, *, keep: str | None = None) -> None:
        document = self.documents.get(code)
        if document is None:
            return
        for version in self.versions[code]:
            if version["status"] == "published" and version["id"] != keep:
                await self.api.post(
                    f"/consent-documents/{document['id']}/versions/"
                    f"{version['id']}/retire"
                )
                self.say(f"  {code}: v{version['version_number']} retirada")

    async def deactivate(self, code: str) -> None:
        document = self.documents.get(code)
        if document is None or not document["is_active"]:
            return
        await self.api.patch(
            f"/consent-documents/{document['id']}",
            {"is_active": False, "activity_reason": DEACTIVATION_REASON},
        )
        self.say(f"  {code}: documento desactivado")

    async def run(self) -> None:
        await self.refresh()

        self.say("1. Quitar VENOPUNCION, PSA y DATOS de los exámenes")
        removed = self.version_ids((*REMOVED_CODES, GENERAL_CODE))
        await self.update_exams(remove=removed, label="sin consentimientos retirados")

        self.say("2. CONSENT_DATOS: versión con el PDF general")
        general_id = await self.ensure_file_version(GENERAL_CODE)
        await self.refresh()
        await self.retire_published(GENERAL_CODE, keep=general_id)

        self.say("3. CONSENT_VIH: versión con su PDF y re-enlace de exámenes")
        hiv_id = await self.ensure_file_version(HIV_CODE)
        await self.refresh()
        if hiv_id is not None:
            old = self.version_ids((HIV_CODE,)) - {hiv_id}
            await self.update_exams(
                replace=dict.fromkeys(old, hiv_id), label="enlazado a la versión nueva"
            )
            await self.retire_published(HIV_CODE, keep=hiv_id)

        self.say("4. Retirar CONSENT_VENOPUNCION y CONSENT_PSA")
        for code in REMOVED_CODES:
            await self.retire_published(code)
            await self.deactivate(code)
        self.say("Transición terminada.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.core.db.seeds.demo.consent_transition",
        description="Transición no destructiva de los documentos a firmar.",
    )
    parser.add_argument(
        "--yes", action="store_true", help="confirma la operación (obligatorio)"
    )
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> None:
    from app.core.database import engine

    database_url = get_settings().database_url
    check_target(database_url, yes=args.yes, action="transicionaría los documentos de")
    print(f"Destino: {describe_target(database_url)}")
    try:
        async with open_api() as api:
            await Transition(api).run()
    except DemoApiError as error:
        print(f"La API rechazó un paso de la transición:\n  {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):  # consola de Windows (cp1252)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        asyncio.run(run(parse_args(argv)))
    except GuardError as error:
        print(error, file=sys.stderr)
        raise SystemExit(error.code) from error


if __name__ == "__main__":
    main()
