"""Tests end-to-end (HTTP) de `/api/v1/catalogs/*` (BD real, transaccion revertida)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.catalogs import CATALOGS

BASE = "/api/v1/catalogs"

# slug -> columnas de comportamiento que debe traer cada fila.
BEHAVIOR = {
    "consent-document-types": set(),
    "consent-signers": set(),
    "duration-units": {"minutes"},
    "precondition-kinds": set(),
    "precondition-categories": set(),
    "specimen-types": set(),
    "result-types": {
        "uses_option_set",
        "uses_numeric_range",
        "uses_boolean_range",
        "uses_unit",
        "uses_formula",
        "requires_reference_range",
    },
    "sexes": {"is_wildcard"},
    "age-units": {"days"},
}
COMMON = {
    "id",
    "code",
    "name",
    "sort_order",
    "is_active",
    "created_at",
    "updated_at",
}


def _new_code() -> str:
    return f"zz-{uuid4().hex[:20]}"


def _payload(slug: str, **overrides: object) -> dict:
    """Body minimo valido de `POST` para el catalogo."""
    body: dict = {"code": _new_code(), "name": "Elemento de prueba"}
    extras: dict = {
        "duration-units": {"minutes": 7},
        "result-types": {
            "uses_option_set": False,
            "uses_numeric_range": True,
            "uses_boolean_range": False,
            "uses_unit": True,
            "uses_formula": False,
            "requires_reference_range": False,
        },
        "sexes": {"is_wildcard": False},
        "age-units": {"days": 7},
    }
    return {**body, **extras.get(slug, {}), **overrides}


def test_registry_covers_the_nine_catalogs() -> None:
    assert {spec.slug for spec in CATALOGS} == set(BEHAVIOR)


@pytest.mark.parametrize("slug", sorted(BEHAVIOR))
async def test_list_returns_active_rows_ordered_by_sort_order(
    client: AsyncClient, slug: str
) -> None:
    response = await client.get(f"{BASE}/{slug}")

    assert response.status_code == 200
    rows = response.json()
    assert rows, slug
    assert all(set(row) == COMMON | BEHAVIOR[slug] for row in rows)
    assert all(row["is_active"] for row in rows)
    orders = [row["sort_order"] for row in rows]
    assert orders == sorted(orders)


async def test_list_exposes_the_seeded_behavior(client: AsyncClient) -> None:
    result_types = {
        row["code"]: row for row in (await client.get(f"{BASE}/result-types")).json()
    }
    sexes = {row["code"]: row for row in (await client.get(f"{BASE}/sexes")).json()}
    age_units = {
        row["code"]: row for row in (await client.get(f"{BASE}/age-units")).json()
    }
    duration_units = {
        row["code"]: row for row in (await client.get(f"{BASE}/duration-units")).json()
    }

    assert result_types["calculated"]["uses_formula"] is True
    assert result_types["numeric"]["requires_reference_range"] is True
    assert result_types["titer"]["uses_option_set"] is True
    assert result_types["boolean"]["uses_boolean_range"] is True
    assert [code for code, row in sexes.items() if row["is_wildcard"]] == ["any"]
    assert age_units["anos"]["days"] == 365.25
    assert duration_units["horas"]["minutes"] == 60


@pytest.mark.parametrize("slug", sorted(BEHAVIOR))
async def test_create_edit_and_deactivate_never_delete(
    client: AsyncClient, slug: str
) -> None:
    created = await client.post(f"{BASE}/{slug}", json=_payload(slug, sort_order=9999))
    assert created.status_code == 201
    item = created.json()
    assert item["is_active"] is True

    edited = await client.patch(
        f"{BASE}/{slug}/{item['id']}", json={"name": "Otro nombre", "sort_order": 9998}
    )
    assert edited.status_code == 200
    assert edited.json()["name"] == "Otro nombre"
    assert edited.json()["code"] == item["code"]

    off = await client.patch(
        f"{BASE}/{slug}/{item['id']}",
        json={"is_active": False, "activity_reason": "ya no se usa"},
    )
    assert off.status_code == 200
    assert off.json()["is_active"] is False

    default_codes = {row["code"] for row in (await client.get(f"{BASE}/{slug}")).json()}
    all_codes = {
        row["code"]
        for row in (
            await client.get(f"{BASE}/{slug}", params={"include_inactive": "true"})
        ).json()
    }
    assert item["code"] not in default_codes
    assert item["code"] in all_codes


async def test_deactivation_reason_is_recorded_in_activity(
    client: AsyncClient,
) -> None:
    item = (await client.post(f"{BASE}/age-units", json=_payload("age-units"))).json()
    await client.patch(
        f"{BASE}/age-units/{item['id']}",
        json={"is_active": False, "activity_reason": "obsoleta"},
    )

    events = (
        await client.get(
            "/api/v1/activity",
            params={"entity_type": "age_units", "entity_id": item["id"]},
        )
    ).json()["items"]

    assert events[0]["action"] == "deactivated"
    assert events[0]["reason"] == "obsoleta"


async def test_there_is_no_delete(client: AsyncClient) -> None:
    item = (await client.post(f"{BASE}/sexes", json=_payload("sexes"))).json()

    response = await client.delete(f"{BASE}/sexes/{item['id']}")

    assert response.status_code == 405


@pytest.mark.parametrize("slug", sorted(BEHAVIOR))
async def test_duplicate_code_returns_409(client: AsyncClient, slug: str) -> None:
    body = _payload(slug)
    assert (await client.post(f"{BASE}/{slug}", json=body)).status_code == 201

    response = await client.post(f"{BASE}/{slug}", json=body)

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert response.json()["details"] == {"code": body["code"]}


async def test_patch_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.patch(f"{BASE}/sexes/{uuid4()}", json={"name": "No existe"})

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.parametrize(
    ("slug", "body"),
    [
        ("duration-units", {"minutes": 0}),
        ("age-units", {"days": -1}),
        ("sexes", {"sort_order": -1}),
        ("result-types", {"uses_unit": None}),
    ],
)
async def test_invalid_body_returns_422(
    client: AsyncClient, slug: str, body: dict
) -> None:
    response = await client.post(f"{BASE}/{slug}", json=_payload(slug, **body))

    assert response.status_code == 422


async def test_code_cannot_be_edited(client: AsyncClient) -> None:
    item = (await client.post(f"{BASE}/sexes", json=_payload("sexes"))).json()

    response = await client.patch(
        f"{BASE}/sexes/{item['id']}", json={"code": "otro", "name": "Nuevo"}
    )

    assert response.status_code == 200
    assert response.json()["code"] == item["code"]


async def test_only_one_wildcard_sex(client: AsyncClient) -> None:
    created = await client.post(
        f"{BASE}/sexes", json=_payload("sexes", is_wildcard=True)
    )
    assert created.status_code == 409
    assert created.json()["details"]["code"] == "any"

    other = (await client.post(f"{BASE}/sexes", json=_payload("sexes"))).json()
    patched = await client.patch(
        f"{BASE}/sexes/{other['id']}", json={"is_wildcard": True}
    )
    assert patched.status_code == 409


async def test_behavior_columns_are_editable(client: AsyncClient) -> None:
    item = (
        await client.post(f"{BASE}/result-types", json=_payload("result-types"))
    ).json()

    response = await client.patch(
        f"{BASE}/result-types/{item['id']}",
        json={"uses_formula": True, "uses_unit": False},
    )

    assert response.status_code == 200
    assert response.json()["uses_formula"] is True
    assert response.json()["uses_unit"] is False
    assert response.json()["uses_numeric_range"] is True


async def test_openapi_documents_every_catalog_route(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]

    for slug in BEHAVIOR:
        assert set(paths[f"{BASE}/{slug}"]) == {"get", "post"}
        assert set(paths[f"{BASE}/{slug}/{{item_id}}"]) == {"patch"}
