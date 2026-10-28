"""El contrato `frontend/app/generated/permissions.json` refleja el catalogo."""

import json

from app.core import permissions_export
from app.core.leo import catalog


def test_committed_contract_matches_generated() -> None:
    committed = permissions_export.CONTRACT_PATH.read_bytes().decode("utf-8")
    assert committed == permissions_export.render(), (
        "tags desalineados: ejecuta uv run python -m app.core.permissions_export"
    )
    assert "\r" not in committed


def test_export_gathers_every_module_of_the_leo_sync_catalog() -> None:
    import app.main  # noqa: F401  (como leo_sync: los routers registran sus tags)

    contract = permissions_export.build_contract()
    exported = {a["tag"] for m in contract["modules"] for a in m["actions"]}
    assert exported == set(catalog.tags)


def test_events_are_not_assignable() -> None:
    actions = {
        a["tag"]: a
        for m in permissions_export.build_contract()["modules"]
        for a in m["actions"]
    }
    assert actions["vladimir.settings.update"]["assignable"] is False
    assert actions["vladimir.settings.view"]["assignable"] is True
    assert json.loads(permissions_export.render())["app"] == "vladimir"


def test_check_flags_a_stale_contract(monkeypatch, tmp_path, capsys) -> None:
    stale = tmp_path / "permissions.json"
    stale.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(permissions_export, "CONTRACT_PATH", stale)
    assert permissions_export.main(check=True) == 1
    assert "tags desalineados" in capsys.readouterr().out
