"""Guardas del comando de datos de demostracion (sin BD).

Un comando que hace `TRUNCATE` debe negarse sin confirmacion y fuera de
localhost, ANTES de abrir ninguna conexion.
"""

import importlib
from types import SimpleNamespace

import pytest

from app.core.db.base import Base
from app.core.db.seeds.demo.guard import (
    GuardError,
    check_empty,
    check_target,
    describe_target,
)
from app.core.db.seeds.demo.reset import business_tables, truncate_sql

LOCAL = "postgresql+asyncpg://usuario:clave-falsa@localhost:5432/vladimir"
REMOTE = "postgresql+asyncpg://usuario:clave-falsa@db.produccion.example:5432/vladimir"


def test_destino_remoto_se_rechaza_aunque_haya_confirmacion():
    with pytest.raises(GuardError) as error:
        check_target(REMOTE, yes=True)
    assert error.value.code == 2
    assert "db.produccion.example" in str(error.value)


def test_destino_local_sin_confirmacion_se_rechaza():
    with pytest.raises(GuardError, match="--yes"):
        check_target(LOCAL, yes=False)


def test_el_mensaje_sin_confirmacion_nombra_la_accion_pedida():
    with pytest.raises(GuardError, match="transicionaria los documentos"):
        check_target(LOCAL, yes=False, action="transicionaria los documentos")


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_destino_local_con_confirmacion_se_acepta(host):
    url = check_target(f"postgresql+asyncpg://u:p@{host}:5432/vladimir", yes=True)
    assert url.database == "vladimir"


def test_la_descripcion_del_destino_no_expone_la_contrasena():
    description = describe_target(LOCAL)
    assert description == "localhost:5432/vladimir"
    assert "clave-falsa" not in description


def test_sin_reset_se_rechaza_una_bd_con_datos():
    with pytest.raises(GuardError, match="lab_areas=2"):
        check_empty({"lab_areas": 2, "staff": 0})


def test_sin_reset_una_bd_vacia_se_acepta():
    check_empty({"lab_areas": 0, "staff": 0})


def test_el_reset_cubre_todas_las_tablas_y_no_toca_alembic_version():
    tables = business_tables()
    assert set(tables) == {t.name for t in Base.metadata.tables.values()}
    assert "activity_events" in tables
    sql = truncate_sql(tables)
    assert sql.startswith("TRUNCATE TABLE ")
    assert sql.endswith(" RESTART IDENTITY CASCADE")
    assert "alembic_version" not in sql


def test_el_comando_aborta_con_host_remoto_antes_de_conectar(monkeypatch, capsys):
    cli = importlib.import_module("app.core.db.seeds.demo.__main__")
    monkeypatch.setattr(
        cli, "get_settings", lambda: SimpleNamespace(database_url=REMOTE)
    )
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--reset", "--yes"])
    assert exit_info.value.code == 2
    assert "ABORTADO" in capsys.readouterr().err


def test_el_comando_exige_yes(monkeypatch, capsys):
    cli = importlib.import_module("app.core.db.seeds.demo.__main__")
    monkeypatch.setattr(
        cli, "get_settings", lambda: SimpleNamespace(database_url=LOCAL)
    )
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--reset"])
    assert exit_info.value.code == 2
    assert "--yes" in capsys.readouterr().err
