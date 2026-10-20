"""Smoke de la integracion con Leo en `app.main`."""

from httpx import ASGITransport, AsyncClient

from app.conftest import FakeLeo
from app.core.config import get_settings
from app.main import app, lifespan

ORIGIN = get_settings().cors_origins_list[0]


async def test_auth_routes_are_mounted(client: AsyncClient, leo: FakeLeo) -> None:
    leo.user = None
    # /auth/me sin sesion: 401 con el formato {code, message, details}.
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


async def test_all_business_modules_require_session(
    client: AsyncClient, leo: FakeLeo
) -> None:
    leo.user = None  # sin sesion: ningun modulo de negocio queda abierto
    for path in (
        "/api/v1/staff",
        "/api/v1/lab-areas",
        "/api/v1/lab-tests",
        "/api/v1/preconditions",
        "/api/v1/samples",
        "/api/v1/print-labels",
        "/api/v1/result-templates",
        "/api/v1/units",
        "/api/v1/analytes",
        "/api/v1/result-option-sets",
        "/api/v1/consent-documents",
    ):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["code"] == "not_authenticated", path


async def test_external_app_endpoints_do_not_need_user_session(
    client: AsyncClient, leo: FakeLeo
) -> None:
    """Integracion con la app externa (tag `integracion`): sin sesion de usuario
    hasta que exista la autenticacion maquina a maquina."""
    leo.user = None
    for path in (
        "/api/v1/consent-documents/data-treatment/current",
        "/api/v1/consent-document-versions/00000000-0000-0000-0000-000000000001/file",
    ):
        response = await client.get(path)
        assert response.status_code not in (401, 403), path


async def test_cors_allows_credentials_and_dpop_header(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/lab-areas",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "dpop,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "dpop" in allowed and "content-type" in allowed


async def test_real_auth_without_cookies_returns_401() -> None:
    """Sin el doble de `current_user`: el SDK real rechaza una peticion sin sesion."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as raw:
        for path in ("/auth/me", "/api/v1/lab-areas"):
            response = await raw.get(path)
            assert response.status_code == 401, path
            assert response.json()["code"] == "not_authenticated"


async def test_lifespan_checks_catalog() -> None:
    async with lifespan(app):  # check_catalog no lanza: todo tag esta declarado
        pass
