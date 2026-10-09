"""Cliente de la API en proceso (httpx + ASGI sobre `app.main:app`).

Toda la carga de datos de demostracion pasa por aqui, es decir por los
mismos routers/controllers/repositories que usa la aplicacion: asi aplican
validaciones, versionado, reglas de activos y triggers de actividad. Una
regla que rechaza un dato se ve como `DemoApiError` (se corrige el dato, no
la regla).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

API_PREFIX = "/api/v1"
PAGE_SIZE = 200  # maximo que admite `pagination_params`


class DemoApiError(RuntimeError):
    """La API rechazo una peticion de la carga de demostracion."""

    def __init__(self, method: str, path: str, status: int, body: Any) -> None:
        self.method, self.path, self.status, self.body = method, path, status, body
        super().__init__(f"{method} {path} -> {status}: {body}")


class DemoApi:
    """Envoltorio fino: levanta `DemoApiError` si la respuesta no es 2xx."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def request(
        self, method: str, path: str, json: Any = None, params: dict | None = None
    ) -> Any:
        response = await self._client.request(
            method, f"{API_PREFIX}{path}", json=json, params=params
        )
        body: Any = response.json() if response.content else None
        if response.is_error:
            raise DemoApiError(method, path, response.status_code, body)
        return body

    async def get(self, path: str, **params: Any) -> Any:
        return await self.request("GET", path, params=params or None)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self.request("POST", path, json=json)

    async def put(self, path: str, json: Any = None) -> Any:
        return await self.request("PUT", path, json=json)

    async def patch(self, path: str, json: Any = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def get_all(self, path: str, **params: Any) -> list[dict]:
        """Todas las paginas de un listado paginado (`Page[...]`)."""
        items: list[dict] = []
        page = 1
        while True:
            data = await self.get(path, page=page, page_size=PAGE_SIZE, **params)
            items.extend(data["items"])
            if len(items) >= data["total"]:
                return items
            page += 1


@asynccontextmanager
async def open_api() -> AsyncIterator[DemoApi]:
    """API en proceso sobre la app real (usa `DATABASE_URL` del `.env`)."""
    from app.main import app  # import tardio: crea el engine al usarse

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://demo") as c:
        yield DemoApi(c)
