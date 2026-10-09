"""Verificacion de integridad del dataset ya cargado, por la API (lo que ve
el frontend / la app externa). Devuelve la lista de problemas (vacia = OK).
"""

from app.core.db.seeds.demo import consent_files, lab_tests
from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry
from app.modules.consent_documents.schemas import DATA_TREATMENT_TYPE


async def _check_versioned(
    api: DemoApi,
    problems: list[str],
    *,
    kind: str,
    catalog_path: str,
    version_path: str,
    codes_to_ids: dict[str, str],
) -> None:
    for code, owner_id in codes_to_ids.items():
        versions = await api.get_all(f"{catalog_path}/{owner_id}/versions")
        if [v["version_number"] for v in versions] != [1]:
            problems.append(f"{kind} {code}: versiones inesperadas {versions}")
            continue
        version = versions[0]
        if version["status"] != "published" or version["published_at"] is None:
            problems.append(f"{kind} {code}: la versión 1 no está publicada")
        detail = await api.get(f"{version_path}/{version['id']}")
        if detail["owner"]["code"] != code or not detail["owner"]["is_active"]:
            problems.append(f"{kind} {code}: dueño inconsistente {detail['owner']}")


async def _check_consent_files(
    api: DemoApi, problems: list[str], registry: Registry
) -> None:
    """Cada version publicada de un documento tiene su PDF (el del manifest) y
    hay exactamente un consentimiento general activo, vigente por la API."""
    manifest = consent_files.load_manifest()
    for code, version_id in registry.consent_versions.items():
        file = await api.get(f"/consent-document-versions/{version_id}/file")
        if file["sha256"] != manifest[code]["pdf_sha256"]:
            problems.append(f"Documento {code}: el PDF no es el del manifest")
    general = [
        d
        for d in await api.get_all("/consent-documents", active="true")
        if d["document_type"] == DATA_TREATMENT_TYPE
    ]
    if len(general) != 1:
        problems.append(
            f"Hay {len(general)} consentimientos generales activos (se espera 1)"
        )
    current = await api.get("/consent-documents/data-treatment/current")
    if current["file"] is None:
        problems.append("El consentimiento general vigente no tiene archivo")


async def verify(api: DemoApi, registry: Registry) -> list[str]:
    problems: list[str] = []

    await _check_versioned(
        api,
        problems,
        kind="Plantilla",
        catalog_path="/result-templates",
        version_path="/result-template-versions",
        codes_to_ids=registry.templates,
    )
    await _check_versioned(
        api,
        problems,
        kind="Etiqueta",
        catalog_path="/print-labels",
        version_path="/print-label-versions",
        codes_to_ids=registry.labels,
    )
    await _check_versioned(
        api,
        problems,
        kind="Documento",
        catalog_path="/consent-documents",
        version_path="/consent-document-versions",
        codes_to_ids=registry.consents,
    )

    inactive_sample_types = {
        sample_type["id"]
        for sample in await api.get_all("/samples")
        for sample_type in sample["types"]
        if not sample_type["is_active"]
    }
    inactive_preconditions = {
        p["id"] for p in await api.get_all("/preconditions", active="false")
    }
    inactive_areas = {a["id"] for a in await api.get_all("/lab-areas", active="false")}
    published_versions = {
        *registry.label_versions.values(),
        *registry.template_versions.values(),
        *registry.consent_versions.values(),
    }

    seeds_by_code = {t.code: t for t in lab_tests.LAB_TESTS}
    for code, test_id in registry.lab_tests.items():
        test = await api.get(f"/lab-tests/{test_id}")
        if not test["is_active"]:
            problems.append(f"Examen {code}: inactivo")
        if test["area_id"] in inactive_areas:
            problems.append(f"Examen {code}: área inactiva")
        for field in ("print_label_version_id", "result_template_version_id"):
            if test[field] not in published_versions:
                problems.append(f"Examen {code}: {field} no es una versión publicada")
        sample_types = [s for s in test["sample_types"] if s["is_active"]]
        if not sample_types or sum(s["is_preferred"] for s in sample_types) != 1:
            problems.append(f"Examen {code}: tipos de muestra sin un único preferido")
        if any(s["sample_type_id"] in inactive_sample_types for s in sample_types):
            problems.append(f"Examen {code}: usa un tipo de muestra inactivo")
        if any(
            p["precondition_id"] in inactive_preconditions
            for p in test["preconditions"]
        ):
            problems.append(f"Examen {code}: usa una precondición inactiva")
        consent_ids = [
            c["consent_document_version_id"] for c in test["consent_documents"]
        ]
        if any(c not in published_versions for c in consent_ids):
            problems.append(f"Examen {code}: documentos a firmar inválidos")
        expected = [
            registry.consent_versions[c]
            for c in lab_tests.consent_codes(seeds_by_code[code])
        ]
        if sorted(consent_ids) != sorted(expected):
            problems.append(f"Examen {code}: documentos a firmar inesperados")

    await _check_consent_files(api, problems, registry)

    activity = await api.get(
        "/activity",
        entity_type="analytes",
        entity_id=registry.analytes["CKMB"],
    )
    if [e["action"] for e in activity["items"]][:1] != ["deactivated"]:
        problems.append("Actividad: el analito desactivado no registra 'deactivated'")
    return problems
