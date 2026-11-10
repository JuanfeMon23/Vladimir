"""Permisos de Leo y auditoria del modulo `catalogs` (con un Leo falso).

Un servicio (p. ej. Incubus con el rol `catalogo-lectura`) entra por el mismo
`require_action` que los usuarios: aqui se simula con un usuario que solo
tiene `vladimir.catalogs.view`.
"""

import pytest
from httpx import AsyncClient

from app.conftest import FakeLeo
from app.core.leo import catalog
from app.modules.catalogs import permissions as p

BASE = "/api/v1/catalogs"
ALL_TAGS = {p.VIEW, p.CREATE, p.EDIT, p.CHANGE_STATUS}
ID1 = "00000000-0000-0000-0000-000000000001"


def test_tags_are_declared_in_the_leo_catalog() -> None:
    assert ALL_TAGS <= set(catalog.tags)
    assert p.VIEW == "vladimir.catalogs.view"


async def test_no_session_returns_401(client: AsyncClient, leo: FakeLeo) -> None:
    leo.user = None

    response = await client.get(f"{BASE}/result-types")

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize(
    ("method", "path", "tag", "body"),
    [
        ("GET", f"{BASE}/sexes", p.VIEW, None),
        ("GET", f"{BASE}/age-units", p.VIEW, None),
        ("POST", f"{BASE}/sexes", p.CREATE, {"code": "x", "name": "X"}),
        ("PATCH", f"{BASE}/sexes/{ID1}", p.EDIT, {"name": "Y"}),
        ("PATCH", f"{BASE}/sexes/{ID1}", p.CHANGE_STATUS, {"is_active": False}),
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
    assert [(event["action_tag"], event["result"]) for event in leo.events] == [
        (tag, "denied")
    ]


async def test_read_only_service_can_read_every_catalog_but_not_write(
    client: AsyncClient, leo: FakeLeo
) -> None:
    leo.grant(p.VIEW)

    for slug in ("result-types", "sexes", "age-units", "duration-units"):
        assert (await client.get(f"{BASE}/{slug}")).status_code == 200
    created = await client.post(f"{BASE}/sexes", json={"code": "x", "name": "X"})

    assert created.status_code == 403
    assert created.json()["details"] == {"action": p.CREATE}


async def test_patch_status_only_does_not_need_edit(
    client: AsyncClient, leo: FakeLeo
) -> None:
    item = (
        await client.post(
            f"{BASE}/age-units", json={"code": "zz-p1", "name": "P", "days": 2}
        )
    ).json()
    leo.grant(p.CHANGE_STATUS)

    response = await client.patch(
        f"{BASE}/age-units/{item['id']}", json={"is_active": False}
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_patch_data_without_edit_is_forbidden_even_with_status(
    client: AsyncClient, leo: FakeLeo
) -> None:
    item = (
        await client.post(
            f"{BASE}/age-units", json={"code": "zz-p2", "name": "P", "days": 2}
        )
    ).json()
    leo.grant(p.CHANGE_STATUS)

    response = await client.patch(
        f"{BASE}/age-units/{item['id']}", json={"name": "Otro", "is_active": False}
    )

    assert response.status_code == 403
    assert response.json()["details"] == {"action": p.EDIT}


async def test_mutations_are_audited(client: AsyncClient, leo: FakeLeo) -> None:
    item = (
        await client.post(
            f"{BASE}/age-units", json={"code": "zz-p3", "name": "P", "days": 2}
        )
    ).json()
    await client.patch(f"{BASE}/age-units/{item['id']}", json={"name": "Nuevo"})
    await client.patch(
        f"{BASE}/age-units/{item['id']}",
        json={"is_active": False, "activity_reason": "cierre"},
    )

    actions = [(event["action_tag"], event["entity_type"]) for event in leo.events]

    assert actions == [
        (p.CREATE, "age_units"),
        (p.EDIT, "age_units"),
        (p.CHANGE_STATUS, "age_units"),
    ]
    assert leo.events[2]["reason"] == "cierre"
