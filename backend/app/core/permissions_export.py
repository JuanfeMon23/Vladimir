"""Exporta el catalogo de permisos de Vladimir al contrato con el frontend.

    cd backend; uv run python -m app.core.permissions_export [--check]

Escribe `frontend/app/generated/permissions.json` (artefacto generado y
commiteado; el frontend deriva de el nombres, tags de pruebas y verificaciones
de alineacion). `--check` sale con codigo 1 si el archivo difiere del catalogo.
No toca la BD ni arranca servicios: solo importa los `permissions.py`.
"""

import argparse
import importlib
import json
import pkgutil
import sys
from pathlib import Path
from typing import Any

import app.modules
from app.core.leo import APP_SLUG, catalog

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "frontend/app/generated/permissions.json"
EVENT_PREFIX = "Evento:"


def load_catalog() -> None:
    """Importa el `permissions.py` de cada modulo: cada uno puebla `catalog`."""
    for info in pkgutil.iter_modules(app.modules.__path__):
        if info.ispkg:
            importlib.import_module(f"app.modules.{info.name}.permissions")


def build_contract() -> dict[str, Any]:
    load_catalog()
    modules = []
    for module in sorted(catalog.to_payload()["modules"], key=lambda m: m["slug"]):
        actions = [
            {
                "tag": f"{APP_SLUG}.{module['slug']}.{action['verb']}",
                "verb": action["verb"],
                "name": action["name"],
                "description": action.get("description", ""),
                "assignable": not action["name"].startswith(EVENT_PREFIX),
            }
            for action in sorted(module.get("actions", []), key=lambda a: a["verb"])
        ]
        modules.append(
            {
                "slug": module["slug"],
                "name": module["name"],
                "description": module.get("description", ""),
                "actions": actions,
            }
        )
    return {"app": APP_SLUG, "modules": modules}


def render() -> str:
    return json.dumps(build_contract(), ensure_ascii=False, indent=2) + "\n"


def main(check: bool) -> int:
    content = render()
    if check:
        current = CONTRACT_PATH.read_bytes().decode("utf-8") if CONTRACT_PATH.exists() else ""
        if current != content:
            print("tags desalineados: ejecuta uv run python -m app.core.permissions_export")
            return 1
        return 0
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_bytes(content.encode("utf-8"))  # LF, sin traduccion de saltos
    print(f"Escrito {CONTRACT_PATH}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    sys.exit(main(parser.parse_args().check))
