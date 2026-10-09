"""Tests de `Settings`: toda variable de entorno es obligatoria y viene de `.env`."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

FAKE_DSN = "postgresql+asyncpg://usuario:clave-falsa@localhost:5432/vladimir"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)


def _load() -> Settings:
    # `_env_file=None`: el test no depende del `backend/.env` local.
    return Settings(_env_file=None)


def test_sin_variables_falla_nombrando_las_obligatorias() -> None:
    with pytest.raises(ValidationError) as error:
        _load()
    missing = {e["loc"][0] for e in error.value.errors() if e["type"] == "missing"}
    assert missing == {"database_url", "cors_origins"}


def test_falta_cors_origins_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", FAKE_DSN)
    with pytest.raises(ValidationError, match="cors_origins"):
        _load()


def test_falta_database_url_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    with pytest.raises(ValidationError, match="database_url"):
        _load()


def test_con_ambas_variables_se_parsean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", FAKE_DSN)
    monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example,")
    settings = _load()
    assert settings.database_url == FAKE_DSN
    assert settings.cors_origins_list == ["http://a.example", "http://b.example"]


def test_ningun_campo_tiene_valor_por_defecto_grabado() -> None:
    assert all(f.is_required() for f in Settings.model_fields.values())
