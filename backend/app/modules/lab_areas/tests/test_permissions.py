"""Permisos de Leo y auditoria del modulo `lab_areas` (con un Leo falso)."""

import pytest
from httpx import AsyncClient

from app.conftest import FakeLeo
from app.core.leo import auth, catalog
from app.modules.lab_areas import permissions as p
from app.modules.staff.models import Staff

BASE = "/api/v1/lab-areas"
ALL_TAGS = {p.VIEW, p.CREATE, p.EDIT, p.CHANGE_STATUS, p.ASSIGN_MANAGER}
ID1 = "00000000-0000-0000-0000-000000000001"
ID2 = "00000000-0000-0000-0000-000000000002"


async def test_no_session_returns_401(client: AsyncClient, leo: FakeLeo) -> None:
    leo.user = None
    response = await client.get(BASE)
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(
    ("method", "path", "tag", "body"),
    [
        ("GET", BASE, p.VIEW, None),
        ("GET", f"{BASE}/{ID1}", p.VIEW, None),
        ("GET", f"{BASE}/{ID1}/manager-history", p.VIEW, None),
        ("POST", BASE, p.CREATE, {"code": "x", "name": "X"}),
        ("PATCH", f"{BASE}/{ID1}", p.EDIT, {"name": "Y"}),
        ("PATCH", f"{BASE}/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
        ("PUT", f"{BASE}/{ID1}/manager", p.ASSIGN_MANAGER, {"staff_id": ID2}),
    ],
)
async def test_missing_tag_returns_403_and_denied_event(
    client: AsyncClient,
    leo: FakeLeo,
    method: str,
    path: str,
    tag: str,
    body: dict | None,
) -> None:
    leo.grant(*(ALL_TAGS - {tag}))
    response = await client.request(method, path, json=body)
    assert response.status_code == 403
    assert response.json()["details"] == {"action": tag}
    assert [(e["action_tag"], e["result"]) for e in leo.events] == [(tag, "denied")]


async def test_with_tag_returns_200(client: AsyncClient, leo: FakeLeo) -> None:
    leo.grant(p.VIEW)
    response = await client.get(BASE)
    assert response.status_code == 200


async def test_patch_status_only_does_not_need_edit(
    client: AsyncClient, leo: FakeLeo, lab_area_payload: dict
) -> None:
    created = (await client.post(BASE, json=lab_area_payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={"is_active": False, "activity_reason": "x"}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_patch_data_without_edit_is_forbidden_even_with_status(
    client: AsyncClient, leo: FakeLeo, lab_area_payload: dict
) -> None:
    created = (await client.post(BASE, json=lab_area_payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={"name": "Otro", "is_active": False}
    )
    assert response.status_code == 403
    assert response.json()["details"] == {"action": p.EDIT}


async def test_mutations_are_audited_with_diff(
    client: AsyncClient, leo: FakeLeo, lab_area_payload: dict
) -> None:
    created = (await client.post(BASE, json=lab_area_payload)).json()
    await client.patch(f"{BASE}/{created['id']}", json={"name": "Nuevo"})
    await client.patch(
        f"{BASE}/{created['id']}",
        json={"is_active": False, "activity_reason": "cierre"},
    )
    create_ev, edit_ev, status_ev = leo.events
    assert create_ev["action_tag"] == p.CREATE
    assert create_ev["entity_type"] == "lab_area"
    assert create_ev["entity_id"] == created["id"]
    assert create_ev["changes"]["code"] == {
        "before": None,
        "after": lab_area_payload["code"],
    }
    assert edit_ev["action_tag"] == p.EDIT
    assert edit_ev["changes"] == {"name": {"before": "Microbiologia", "after": "Nuevo"}}
    assert status_ev["action_tag"] == p.CHANGE_STATUS
    assert status_ev["changes"] == {"is_active": {"before": True, "after": False}}
    assert status_ev["reason"] == "cierre"
    assert edit_ev["actor"]["jkt"] == "jkt-falso"


async def test_assign_manager_is_audited(
    client: AsyncClient, leo: FakeLeo, lab_area_payload: dict, active_staff: Staff
) -> None:
    created = (await client.post(BASE, json=lab_area_payload)).json()
    response = await client.put(
        f"{BASE}/{created['id']}/manager", json={"staff_id": str(active_staff.id)}
    )
    assert response.status_code == 200
    event = leo.events[-1]
    assert event["action_tag"] == p.ASSIGN_MANAGER
    assert event["changes"]["staff_id"]["after"] == str(active_staff.id)


async def test_leo_down_does_not_break_business_operation(
    client: AsyncClient, leo: FakeLeo, lab_area_payload: dict
) -> None:
    leo.down = True
    response = await client.post(BASE, json=lab_area_payload)
    assert response.status_code == 201
    assert leo.events == []


async def test_failing_audit_never_propagates(
    client: AsyncClient,
    lab_area_payload: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*_a: object, **_k: object) -> bool:
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(auth.audit, "record", boom)
    response = await client.post(BASE, json=lab_area_payload)
    assert response.status_code == 201


def test_catalog_matches_require_action() -> None:
    auth.check_catalog()  # ningun tag usado sin declarar
    declared = {t for t in catalog.tags if t.startswith("vladimir.lab-areas.")}
    used = {t for t in auth.used_tags if t.startswith("vladimir.lab-areas.")}
    assert declared == used == ALL_TAGS


def test_catalog_payload_has_readable_unique_names() -> None:
    payload = catalog.to_payload()
    (module,) = [m for m in payload["modules"] if m["slug"] == "lab-areas"]
    assert module["name"] == "Áreas de laboratorio"
    names = [a["name"] for a in module["actions"]]
    assert len(set(names)) == len(names) == 5
