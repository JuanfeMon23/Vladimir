"""Permisos de Leo y auditoria del modulo `consent_documents` (con un Leo falso)."""

import pytest
from httpx import AsyncClient

from app.conftest import FakeLeo
from app.core.leo import auth, catalog
from app.modules.consent_documents import permissions as p

BASE = "/api/v1/consent-documents"
SLUG = "consent-documents"
ENTITY = "consent_document"
VERSION_ENTITY = "consent_document_version"
MODULE_NAME = "Documentos a firmar"
ID1 = "00000000-0000-0000-0000-000000000001"
V1 = "00000000-0000-0000-0000-000000000002"

ALL_TAGS = {
    p.VIEW,
    p.CREATE,
    p.EDIT,
    p.CHANGE_STATUS,
    p.CREATE_VERSION,
    p.EDIT_VERSION,
    p.PUBLISH_VERSION,
    p.RETIRE_VERSION,
}
KEY_FIELD = "code"
EDIT_FIELD, EDIT_VALUE = "name", "Consentimiento v2"
CASES = [
    ("GET", BASE, p.VIEW, None),
    ("GET", f"{BASE}/{ID1}", p.VIEW, None),
    ("GET", f"{BASE}/{ID1}/versions", p.VIEW, None),
    ("GET", f"/api/v1/consent-document-versions/{V1}", p.VIEW, None),
    (
        "POST",
        BASE,
        p.CREATE,
        {"code": "x", "name": "X", "document_type": "consentimiento_informado"},
    ),
    ("PATCH", f"{BASE}/{ID1}", p.EDIT, {"name": "Y"}),
    ("PATCH", f"{BASE}/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
    ("POST", f"{BASE}/{ID1}/versions", p.CREATE_VERSION, {}),
    ("PATCH", f"{BASE}/{ID1}/versions/{V1}", p.EDIT_VERSION, {"change_notes": "n"}),
    ("POST", f"{BASE}/{ID1}/versions/{V1}/publish", p.PUBLISH_VERSION, None),
    ("POST", f"{BASE}/{ID1}/versions/{V1}/retire", p.RETIRE_VERSION, None),
]


@pytest.fixture
def payload(consent_document_payload: dict) -> dict:
    return consent_document_payload


async def test_no_session_returns_401(client: AsyncClient, leo: FakeLeo) -> None:
    leo.user = None
    response = await client.get(BASE)
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(("method", "path", "tag", "body"), CASES)
async def test_missing_tag_returns_403_and_denied_event(
    client: AsyncClient,
    leo: FakeLeo,
    method: str,
    path: str,
    tag: str,
    body: object,
) -> None:
    leo.grant(*(ALL_TAGS - {tag}))
    response = await client.request(method, path, json=body)
    assert response.status_code == 403
    assert response.json()["details"] == {"action": tag}
    assert [(e["action_tag"], e["result"]) for e in leo.events] == [(tag, "denied")]


async def test_with_view_tag_returns_200(client: AsyncClient, leo: FakeLeo) -> None:
    leo.grant(p.VIEW)
    assert (await client.get(BASE)).status_code == 200


async def test_patch_status_only_does_not_need_edit(
    client: AsyncClient, leo: FakeLeo, payload: dict
) -> None:
    created = (await client.post(BASE, json=payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={"is_active": False, "activity_reason": "x"}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_patch_data_without_edit_is_forbidden_even_with_status(
    client: AsyncClient, leo: FakeLeo, payload: dict
) -> None:
    created = (await client.post(BASE, json=payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={EDIT_FIELD: EDIT_VALUE, "is_active": False}
    )
    assert response.status_code == 403
    assert response.json()["details"] == {"action": p.EDIT}


async def test_create_edit_and_status_are_audited_with_diff(
    client: AsyncClient, leo: FakeLeo, payload: dict
) -> None:
    created = (await client.post(BASE, json=payload)).json()
    await client.patch(f"{BASE}/{created['id']}", json={EDIT_FIELD: EDIT_VALUE})
    await client.patch(
        f"{BASE}/{created['id']}",
        json={"is_active": False, "activity_reason": "cierre"},
    )
    create_ev, edit_ev, status_ev = leo.events
    assert create_ev["action_tag"] == p.CREATE
    assert create_ev["entity_type"] == ENTITY
    assert create_ev["entity_id"] == created["id"]
    assert create_ev["changes"][KEY_FIELD] == {
        "before": None,
        "after": payload[KEY_FIELD],
    }
    assert edit_ev["action_tag"] == p.EDIT
    assert edit_ev["changes"] == {
        EDIT_FIELD: {"before": payload[EDIT_FIELD], "after": EDIT_VALUE}
    }
    assert status_ev["action_tag"] == p.CHANGE_STATUS
    assert status_ev["changes"] == {"is_active": {"before": True, "after": False}}
    assert status_ev["reason"] == "cierre"
    assert edit_ev["actor"]["jkt"] == "jkt-falso"


async def test_leo_down_does_not_break_business_operation(
    client: AsyncClient, leo: FakeLeo, payload: dict
) -> None:
    leo.down = True
    response = await client.post(BASE, json=payload)
    assert response.status_code == 201
    assert leo.events == []


async def test_failing_audit_never_propagates(
    client: AsyncClient, payload: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_a: object, **_k: object) -> bool:
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(auth.audit, "record", boom)
    assert (await client.post(BASE, json=payload)).status_code == 201


def test_catalog_matches_require_action() -> None:
    auth.check_catalog()  # ningun tag usado sin declarar
    prefix = f"vladimir.{SLUG}."
    declared = {t for t in catalog.tags if t.startswith(prefix)}
    used = {t for t in auth.used_tags if t.startswith(prefix)}
    assert declared == used == ALL_TAGS


def test_catalog_payload_has_readable_unique_names() -> None:
    payload = catalog.to_payload()
    (module,) = [m for m in payload["modules"] if m["slug"] == SLUG]
    assert module["name"] == MODULE_NAME
    names = [a["name"] for a in module["actions"]]
    assert len(set(names)) == len(names) == len(ALL_TAGS)


async def test_version_lifecycle_is_audited(
    client: AsyncClient,
    leo: FakeLeo,
    payload: dict,
    consent_document_version_payload: dict,
) -> None:
    parent = (await client.post(BASE, json=payload)).json()
    base = f"{BASE}/{parent['id']}/versions"
    version = (await client.post(base, json=consent_document_version_payload)).json()
    await client.patch(f"{base}/{version['id']}", json={"change_notes": "ajuste"})
    assert (await client.post(f"{base}/{version['id']}/publish")).status_code == 200
    assert (await client.post(f"{base}/{version['id']}/retire")).status_code == 200

    _, created_ev, edit_ev, publish_ev, retire_ev = leo.events
    assert created_ev["action_tag"] == p.CREATE_VERSION
    assert created_ev["entity_type"] == VERSION_ENTITY
    assert created_ev["entity_id"] == version["id"]
    assert created_ev["changes"]["status"] == {"before": None, "after": "draft"}
    assert edit_ev["action_tag"] == p.EDIT_VERSION
    assert edit_ev["changes"] == {"change_notes": {"before": None, "after": "ajuste"}}
    assert publish_ev["action_tag"] == p.PUBLISH_VERSION
    assert publish_ev["changes"]["status"] == {"before": "draft", "after": "published"}
    assert retire_ev["action_tag"] == p.RETIRE_VERSION
    assert retire_ev["changes"]["status"] == {"before": "published", "after": "retired"}


async def test_external_app_endpoints_stay_open_without_session(
    client: AsyncClient, leo: FakeLeo
) -> None:
    """Integracion con la app de firmas: sin sesion de usuario (autenticacion
    maquina a maquina pendiente). Responden 404 de negocio, nunca 401/403."""
    leo.user = None
    for path in (
        f"{BASE}/data-treatment/current",
        f"/api/v1/consent-document-versions/{V1}/file",
    ):
        response = await client.get(path)
        assert response.status_code not in (401, 403), path
