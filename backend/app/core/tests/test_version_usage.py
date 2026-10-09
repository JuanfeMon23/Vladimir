"""Registro de usos de versiones (`register_version_usage`): el nucleo
bloquea `VersioningService.retire` si algun modulo registrado reporta que la
version esta en uso, sin conocer a ese modulo."""

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import versioning
from app.core.versioning import (
    PUBLISHED,
    RETIRED,
    VersioningService,
    VersionInUseError,
    register_version_usage,
)

FAKE_TABLE = "zz_fake_versions"


class _FakeVersion:
    __tablename__ = FAKE_TABLE


def _published() -> Any:
    return SimpleNamespace(id=uuid4(), status=PUBLISHED)


@pytest.fixture
def service():
    yield VersioningService(_FakeVersion, "fake_id")
    versioning._version_usage_finders.pop(FAKE_TABLE, None)


async def test_retire_without_registered_usage_succeeds(
    session: AsyncSession, service: VersioningService
) -> None:
    version = await service.retire(session, _published())
    assert version.status == RETIRED


async def test_retire_version_in_use_raises_409_with_sorted_codes(
    session: AsyncSession, service: VersioningService
) -> None:
    version = _published()

    async def finder(_session: AsyncSession, version_id: Any) -> list[str]:
        assert version_id == version.id
        return ["HB", "GLU", "HB"]

    register_version_usage(FAKE_TABLE, finder)

    with pytest.raises(VersionInUseError) as exc_info:
        await service.retire(session, version)

    error = exc_info.value
    assert error.status_code == 409
    assert error.code == "version_in_use"
    assert error.details == {"id": str(version.id), "lab_test_codes": ["GLU", "HB"]}
    assert error.message == (
        "No se puede retirar la versión: la usan exámenes activos (GLU, HB)."
    )
    assert version.status == PUBLISHED


async def test_retire_version_whose_finder_returns_nothing_succeeds(
    session: AsyncSession, service: VersioningService
) -> None:
    async def finder(_session: AsyncSession, _version_id: Any) -> list[str]:
        return []

    register_version_usage(FAKE_TABLE, finder)

    version = await service.retire(session, _published())
    assert version.status == RETIRED
