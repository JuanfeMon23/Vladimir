"""Tests del middleware CORS registrado en `app.main`.

No requieren base de datos: un preflight `OPTIONS` lo responde
`CORSMiddleware` antes de llegar a ningun router.
"""

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app

# Origen permitido segun el `.env` activo (el mismo que leyo la app al importar).
ALLOWED_ORIGIN = get_settings().cors_origins_list[0]


async def test_preflight_options_staff_returns_cors_headers() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/staff",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


async def test_preflight_options_rejects_unknown_origin() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/staff",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers
