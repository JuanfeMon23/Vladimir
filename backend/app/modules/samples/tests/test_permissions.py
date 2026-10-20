"""Permisos de Leo y auditoria del modulo `samples` (con un Leo falso)."""

import pytest
from httpx import AsyncClient

from app.conftest import FakeLeo
from app.core.leo import auth, catalog
from app.modules.samples import permissions as p

BASE = "/api/v1/samples"
TYPES = "/api/v1/sample-types"
SLUG = "samples"
ENTITY = "sample"
MODULE_NAME = "Muestras"
ID1 = "00000000-0000-0000-0000-000000000001"

ALL_TAGS = {p.VIEW, p.CREATE, p.EDIT, p.CHANGE_STATUS, p.ADD_TYPE}
KEY_FIELD = "code"
EDIT_FIELD, EDIT_VALUE = "name", "Orina"
TYPE_BODY = {"code": "x", "name": "X", "specimen": "suero"}
CASES = [
    ("GET", BASE, p.VIEW, None),
    ("GET", f"{BASE}/{ID1}", p.VIEW, None),
    ("GET", f"{BASE}/{ID1}/types", p.VIEW, None),
    ("POST", BASE, p.CREATE, {"code": "x", "name": "X"}),
    ("PATCH", f"{BASE}/{ID1}", p.EDIT, {"name": "Y"}),
    ("PATCH", f"{BASE}/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
    ("POST", f"{BASE}/{ID1}/types", p.ADD_TYPE, TYPE_BODY),
    ("PATCH", f"{TYPES}/{ID1}", p.EDIT, {"name": "Y"}),
    ("PATCH", f"{TYPES}/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
]


@pytest.fixture
def payload(sample_payload: dict) -> dict:
    return sample_payload


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
    assert "types" not in create_ev["changes"]
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


async def test_sample_types_are_audited(
    client: AsyncClient, leo: FakeLeo, payload: dict, sample_type_payload: dict
) -> None:
    parent = (await client.post(BASE, json=payload)).json()
    created = await client.post(
        f"{BASE}/{parent['id']}/types", json=sample_type_payload
    )
    assert created.status_code == 201
    type_id = created.json()["id"]
    edited = await client.patch(f"{TYPES}/{type_id}", json={"name": "Tubo morado"})
    assert edited.status_code == 200
    await client.patch(
        f"{TYPES}/{type_id}", json={"is_active": False, "activity_reason": "ya no"}
    )
    _, add_ev, edit_ev, status_ev = leo.events
    assert add_ev["action_tag"] == p.ADD_TYPE
    assert add_ev["entity_type"] == "sample_type"
    assert add_ev["entity_id"] == type_id
    assert add_ev["changes"]["sample_id"]["after"] == parent["id"]
    assert edit_ev["action_tag"] == p.EDIT
    assert edit_ev["changes"] == {
        "name": {"before": sample_type_payload["name"], "after": "Tubo morado"}
    }
    assert status_ev["action_tag"] == p.CHANGE_STATUS
    assert status_ev["reason"] == "ya no"
