"""Permisos de Leo y auditoria del modulo `result_templates` (con un Leo falso)."""

import pytest
from httpx import AsyncClient

from app.conftest import FakeLeo
from app.core.leo import auth, catalog
from app.modules.result_templates import permissions as p
from app.modules.result_templates.schemas import ResultTemplateVersionRead

API = "/api/v1"
BASE = f"{API}/result-templates"
SLUG = "result-templates"
MODULE_NAME = "Plantillas de resultados"
ID1 = "00000000-0000-0000-0000-000000000001"
V1 = "00000000-0000-0000-0000-000000000002"
A1 = "00000000-0000-0000-0000-000000000003"
R1 = "00000000-0000-0000-0000-000000000004"
VER = f"{BASE}/{ID1}/versions/{V1}"
ANALYTE = f"{VER}/analytes/{A1}"

ALL_TAGS = {
    p.VIEW,
    p.CREATE,
    p.EDIT,
    p.CHANGE_STATUS,
    p.CREATE_VERSION,
    p.EDIT_VERSION,
    p.PUBLISH_VERSION,
    p.RETIRE_VERSION,
    p.EDIT_CONTENT,
    p.MANAGE_UNITS,
    p.MANAGE_ANALYTES,
    p.MANAGE_OPTION_SETS,
}
UNIT_BODY = {"code": "x", "symbol": "x", "name": "X"}
OPTION_BODY = {"code": "x", "label": "X", "sort_order": 1}
RANGE_BODY = {"sex": "any"}
CASES = [
    # Lecturas: todas bajo `view`.
    ("GET", f"{API}/units", p.VIEW, None),
    ("GET", f"{API}/units/{ID1}", p.VIEW, None),
    ("GET", f"{API}/analytes", p.VIEW, None),
    ("GET", f"{API}/analytes/{ID1}", p.VIEW, None),
    ("GET", f"{API}/result-option-sets", p.VIEW, None),
    ("GET", f"{API}/result-option-sets/{ID1}", p.VIEW, None),
    ("GET", f"{API}/result-option-sets/{ID1}/options", p.VIEW, None),
    ("GET", BASE, p.VIEW, None),
    ("GET", f"{BASE}/{ID1}", p.VIEW, None),
    ("GET", f"{BASE}/{ID1}/versions", p.VIEW, None),
    ("GET", f"{API}/result-template-versions/{V1}", p.VIEW, None),
    ("GET", f"{VER}/sections", p.VIEW, None),
    ("GET", f"{VER}/analytes", p.VIEW, None),
    ("GET", f"{ANALYTE}/reference-ranges", p.VIEW, None),
    # Plantilla.
    ("POST", BASE, p.CREATE, {"code": "x", "name": "X"}),
    ("PATCH", f"{BASE}/{ID1}", p.EDIT, {"name": "Y"}),
    ("PATCH", f"{BASE}/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
    # Versionado.
    ("POST", f"{BASE}/{ID1}/versions", p.CREATE_VERSION, {}),
    ("PATCH", VER, p.EDIT_VERSION, {"change_notes": "n"}),
    ("POST", f"{VER}/publish", p.PUBLISH_VERSION, None),
    ("POST", f"{VER}/retire", p.RETIRE_VERSION, None),
    # Contenido del borrador.
    ("POST", f"{VER}/sections", p.EDIT_CONTENT, {"name": "S", "sort_order": 1}),
    ("PATCH", f"{VER}/sections/{A1}", p.EDIT_CONTENT, {"name": "S"}),
    (
        "POST",
        f"{VER}/analytes",
        p.EDIT_CONTENT,
        {"analyte_id": A1, "sort_order": 1, "result_type": "numeric"},
    ),
    ("PATCH", ANALYTE, p.EDIT_CONTENT, {"sort_order": 2}),
    ("POST", f"{ANALYTE}/reference-ranges", p.EDIT_CONTENT, RANGE_BODY),
    ("PATCH", f"{ANALYTE}/reference-ranges/{R1}", p.EDIT_CONTENT, {"low": 1}),
    # Catalogos de apoyo.
    ("POST", f"{API}/units", p.MANAGE_UNITS, UNIT_BODY),
    ("PATCH", f"{API}/units/{ID1}", p.MANAGE_UNITS, {"name": "Y"}),
    ("POST", f"{API}/analytes", p.MANAGE_ANALYTES, {"code": "x", "name": "X"}),
    ("PATCH", f"{API}/analytes/{ID1}", p.MANAGE_ANALYTES, {"name": "Y"}),
    ("POST", f"{API}/result-option-sets", p.MANAGE_OPTION_SETS, UNIT_BODY),
    ("PATCH", f"{API}/result-option-sets/{ID1}", p.MANAGE_OPTION_SETS, {"name": "Y"}),
    (
        "POST",
        f"{API}/result-option-sets/{ID1}/options",
        p.MANAGE_OPTION_SETS,
        OPTION_BODY,
    ),
    ("PATCH", f"{API}/result-options/{ID1}", p.MANAGE_OPTION_SETS, {"label": "Y"}),
]


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
    for path in (BASE, f"{API}/units", f"{API}/analytes", f"{API}/result-option-sets"):
        assert (await client.get(path)).status_code == 200, path


async def test_patch_status_only_does_not_need_edit(
    client: AsyncClient, leo: FakeLeo, result_template_payload: dict
) -> None:
    created = (await client.post(BASE, json=result_template_payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={"is_active": False, "activity_reason": "x"}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_patch_data_without_edit_is_forbidden_even_with_status(
    client: AsyncClient, leo: FakeLeo, result_template_payload: dict
) -> None:
    created = (await client.post(BASE, json=result_template_payload)).json()
    leo.grant(p.CHANGE_STATUS)
    response = await client.patch(
        f"{BASE}/{created['id']}", json={"name": "Otro", "is_active": False}
    )
    assert response.status_code == 403
    assert response.json()["details"] == {"action": p.EDIT}


async def test_template_create_edit_and_status_are_audited_with_diff(
    client: AsyncClient, leo: FakeLeo, result_template_payload: dict
) -> None:
    payload = result_template_payload
    created = (await client.post(BASE, json=payload)).json()
    await client.patch(f"{BASE}/{created['id']}", json={"name": "Perfil v2"})
    await client.patch(
        f"{BASE}/{created['id']}",
        json={"is_active": False, "activity_reason": "cierre"},
    )
    create_ev, edit_ev, status_ev = leo.events
    assert create_ev["action_tag"] == p.CREATE
    assert create_ev["entity_type"] == "result_template"
    assert create_ev["entity_id"] == created["id"]
    assert create_ev["changes"]["code"] == {"before": None, "after": payload["code"]}
    assert edit_ev["action_tag"] == p.EDIT
    assert edit_ev["changes"] == {
        "name": {"before": payload["name"], "after": "Perfil v2"}
    }
    assert status_ev["action_tag"] == p.CHANGE_STATUS
    assert status_ev["changes"] == {"is_active": {"before": True, "after": False}}
    assert status_ev["reason"] == "cierre"
    assert edit_ev["actor"]["jkt"] == "jkt-falso"


async def test_leo_down_does_not_break_business_operation(
    client: AsyncClient, leo: FakeLeo, result_template_payload: dict
) -> None:
    leo.down = True
    response = await client.post(BASE, json=result_template_payload)
    assert response.status_code == 201
    assert leo.events == []


async def test_failing_audit_never_propagates(
    client: AsyncClient,
    result_template_payload: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*_a: object, **_k: object) -> bool:
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(auth.audit, "record", boom)
    assert (await client.post(BASE, json=result_template_payload)).status_code == 201


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


async def test_support_catalogs_are_audited_with_their_own_tag(
    client: AsyncClient,
    leo: FakeLeo,
    unit_payload: dict,
    analyte_payload: dict,
    option_set_payload: dict,
    option_payload: dict,
) -> None:
    unit = (await client.post(f"{API}/units", json=unit_payload)).json()
    await client.patch(
        f"{API}/units/{unit['id']}",
        json={"is_active": False, "activity_reason": "obsoleta"},
    )
    analyte = (await client.post(f"{API}/analytes", json=analyte_payload)).json()
    await client.patch(f"{API}/analytes/{analyte['id']}", json={"name": "Glucemia"})
    option_set = (
        await client.post(f"{API}/result-option-sets", json=option_set_payload)
    ).json()
    option = (
        await client.post(
            f"{API}/result-option-sets/{option_set['id']}/options", json=option_payload
        )
    ).json()
    await client.patch(f"{API}/result-options/{option['id']}", json={"label": "Pos"})

    assert [(e["action_tag"], e["entity_type"]) for e in leo.events] == [
        (p.MANAGE_UNITS, "unit"),
        (p.MANAGE_UNITS, "unit"),
        (p.MANAGE_ANALYTES, "analyte"),
        (p.MANAGE_ANALYTES, "analyte"),
        (p.MANAGE_OPTION_SETS, "result_option_set"),
        (p.MANAGE_OPTION_SETS, "result_option"),
        (p.MANAGE_OPTION_SETS, "result_option"),
    ]
    deactivate = leo.events[1]
    assert deactivate["changes"] == {"is_active": {"before": True, "after": False}}
    assert deactivate["reason"] == "obsoleta"
    assert "default_unit_detail" not in leo.events[2]["changes"]
    assert leo.events[3]["changes"] == {
        "name": {"before": analyte_payload["name"], "after": "Glucemia"}
    }
    assert leo.events[6]["changes"] == {
        "label": {"before": option_payload["label"], "after": "Pos"}
    }


async def test_versions_and_content_are_audited(
    client: AsyncClient, leo: FakeLeo, draft: ResultTemplateVersionRead
) -> None:
    ver = f"{BASE}/{draft.result_template_id}/versions/{draft.id}"
    edited = await client.patch(ver, json={"change_notes": "ajuste"})
    assert edited.status_code == 200
    section = (
        await client.post(f"{ver}/sections", json={"name": "Serie", "sort_order": 1})
    ).json()
    await client.patch(f"{ver}/sections/{section['id']}", json={"name": "Roja"})

    edit_ev, create_ev, patch_ev = leo.events
    assert edit_ev["action_tag"] == p.EDIT_VERSION
    assert edit_ev["entity_type"] == "result_template_version"
    assert edit_ev["entity_id"] == str(draft.id)
    assert edit_ev["changes"] == {"change_notes": {"before": None, "after": "ajuste"}}
    assert create_ev["action_tag"] == p.EDIT_CONTENT
    assert create_ev["entity_type"] == "result_template_section"
    assert create_ev["changes"]["name"] == {"before": None, "after": "Serie"}
    assert patch_ev["action_tag"] == p.EDIT_CONTENT
    assert patch_ev["changes"] == {"name": {"before": "Serie", "after": "Roja"}}


async def test_create_version_is_audited(
    client: AsyncClient, leo: FakeLeo, result_template_payload: dict
) -> None:
    template = (await client.post(BASE, json=result_template_payload)).json()
    version = (
        await client.post(
            f"{BASE}/{template['id']}/versions", json={"report_settings": {}}
        )
    ).json()
    event = leo.events[-1]
    assert event["action_tag"] == p.CREATE_VERSION
    assert event["entity_type"] == "result_template_version"
    assert event["entity_id"] == version["id"]
    assert event["changes"]["status"] == {"before": None, "after": "draft"}
