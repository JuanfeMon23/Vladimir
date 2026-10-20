"""Servicio de versionado: ciclo draft -> published -> retired.

Reglas completas en la nota de bóveda `Versionado` (resumen aplicado aqui):
- Crear version = clonar la ultima version (publicada o retirada) como
  nuevo draft con `version_number + 1`. Si el padre no tiene ninguna, se
  crea la version 1 con los campos del body (los de `required_fields` son
  obligatorios en ese caso).
- Solo existe un draft a la vez por entidad (indice unico parcial en BD,
  ver `core/db/mixins.py::VersionMixin`); `create_version` lo comprueba antes
  (409 por borrador existente, no por la BD).
- Solo se edita o publica un `draft`. Publicar fija `published_at` y la
  version es inmutable desde entonces.
- Retirar solo aplica a una version `published` y no se permite mientras
  este en uso (409 `version_in_use`). Quien la usa lo sabe el modulo
  consumidor (`lab_tests`): registra un buscador de usos por tabla de
  versiones con `register_version_usage` (inversion de dependencia) y
  `retire` lo consulta por `model.__tablename__`. Asi `print_labels`,
  `result_templates` y `consent_documents` no importan `lab_tests` y el
  nucleo no conoce ningun modulo.

El servicio es generico (no conoce `PrintLabel`, `ResultTemplate` ni
`ConsentDocument`). Cada modulo lo instancia una vez en su `controller.py` y
declara solo lo especifico: modelos, nombre del padre, schemas de lectura,
campos obligatorios de la version 1 y, si hace falta, dos hooks:

    versioning = VersioningService(
        PrintLabelVersion,
        "print_label_id",
        parent_model=PrintLabel,
        parent_noun="etiqueta",
        feminine=True,
        read_schema=PrintLabelVersionRead,
        owner_read_schema=PrintLabelVersionWithOwnerRead,
        required_fields=("width_mm", ...),
        validate_publish=...,   # opcional: async (session, version) -> None
        clone_content=...,      # opcional: async (session, source_id, draft_id)
    )
    list_versions = versioning.list_versions
    create_version = versioning.create_version  # ...

Los metodos de alto nivel (`list_versions`, `create_version`,
`update_version`, `publish_version`, `retire_version`, `read_with_owner`)
hacen `commit` y devuelven el `XVersionRead`; los de bajo nivel
(`create_draft`, `ensure_draft`, `publish`, `retire`) solo hacen
`add`/`flush`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active
from app.core.dependencies import PaginationParams
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
    not_found,
)
from app.core.repository import get_or_404, paginate, update_entity
from app.core.schemas import Page, VersionStatus, error_responses

DRAFT = "draft"
PUBLISHED = "published"
RETIRED = "retired"

# `responses=` de las rutas `POST .../versions/{id}/retire` (OpenAPI): el 409
# es `version_in_use` (ver `register_version_usage`).
RETIRE_VERSION_RESPONSES = error_responses(
    404,
    409,
    422,
    descriptions={
        409: "`version_in_use`: la usan exámenes activos (`details.lab_test_codes`)."
    },
)


class VersionOwnerRead(BaseModel):
    """Datos minimos del catalogo dueno de una version (etiqueta, plantilla
    o documento). Lo embebe `GET /api/v1/<x>-versions/{id}` como `owner`,
    para saber a quien pertenece una version conociendo solo su id."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_active: bool


class VersionNotFoundError(NotFoundError):
    """404 de una version buscada solo por su id (sin el padre en la URL).

    `subject`: "una versión de etiqueta", "una versión de plantilla", ...
    """

    def __init__(self, subject: str, version_id: Any) -> None:
        super().__init__(
            message=f"No existe {subject} con id '{version_id}'.",
            details={"id": str(version_id)},
        )


class VersionMissingFieldsError(ValidationAppError):
    """422: faltan campos obligatorios al crear la primera version (no hay
    version previa que clonar) o al publicar (`action`).
    `details={"missing_fields": [...]}`."""

    def __init__(
        self, missing_fields: list[str], action: str = "crear la primera version"
    ) -> None:
        super().__init__(
            message=(
                f"Faltan campos obligatorios para {action}: "
                f"{', '.join(missing_fields)}."
            ),
            details={"missing_fields": missing_fields},
        )


class VersionDraftExistsError(ConflictError):
    """409: el padre ya tiene un borrador; se edita, no se clona de nuevo.
    `parent`: "La etiqueta", `parent_fk`: clave de `details`."""

    def __init__(self, parent: str, parent_fk: str, parent_id: Any) -> None:
        super().__init__(
            message=(
                f"{parent} '{parent_id}' ya tiene un borrador; "
                "edítalo en vez de crear uno nuevo."
            ),
            details={parent_fk: str(parent_id)},
        )


# Columnas del ciclo de vida de version (aportadas por `VersionMixin` o
# propias de cada fila) que nunca se copian al clonar un nuevo draft.
_NON_CLONABLE_COLUMNS = {
    "id",
    "version_number",
    "status",
    "published_at",
    "change_notes",
    "created_at",
    "updated_at",
}


class VersioningService[VersionModelT]:
    """Ciclo de vida generico `draft -> published -> retired` de una entidad
    versionada. Ver el docstring del modulo para como instanciarlo.

    - `model` / `parent_fk`: modelo de version y su columna FK al padre.
    - `parent_model` / `parent_noun` / `feminine`: catalogo padre ("etiqueta",
      `feminine=True`); de ahi salen los mensajes en espanol.
    - `read_schema` / `owner_read_schema`: `XVersionRead` y
      `XVersionWithOwnerRead`.
    - `required_fields`: campos del body obligatorios en la version 1.
    - `publish_required`: `{campo reportado: atributo indicador}` que debe
      estar presente (no `None`) para publicar; si falta, 422
      `VersionMissingFieldsError` con los campos reportados. El indicador
      permite no tocar atributos diferidos (p. ej. `file_base64` ->
      `file_sha256`).
    - `validate_publish(session, version)`: opcional, falla (422) si el
      borrador no esta completo; corre antes de publicar.
    - `clone_content(session, source_version_id, draft_id)`: opcional, copia
      el contenido hijo al clonar un borrador.
    """

    def __init__(
        self,
        model: type[VersionModelT],
        parent_fk: str,
        *,
        parent_model: type | None = None,
        parent_noun: str = "",
        feminine: bool = False,
        read_schema: type[BaseModel] | None = None,
        owner_read_schema: type[BaseModel] | None = None,
        required_fields: tuple[str, ...] = (),
        publish_required: dict[str, str] | None = None,
        validate_publish: Callable[[AsyncSession, Any], Awaitable[None]] | None = None,
        clone_content: Callable[[AsyncSession, UUID, UUID], Awaitable[None]]
        | None = None,
    ) -> None:
        self.model = model
        self.parent_fk = parent_fk
        self.parent_model = parent_model
        self.read_schema = read_schema
        self.owner_read_schema = owner_read_schema
        self.required_fields = required_fields
        self.publish_required = publish_required or {}
        self.validate_publish = validate_publish
        self.clone_content = clone_content
        self._definite = f"{'la' if feminine else 'el'} {parent_noun}"
        self._indefinite = f"{'una' if feminine else 'un'} {parent_noun}"
        self._feminine = feminine
        self._owner_subject = f"una versión de {parent_noun}"

    # --- lectura ---

    async def _parent(self, session: AsyncSession, parent_id: UUID) -> Any:
        return await get_or_404(session, self.parent_model, parent_id, self._indefinite)

    async def get_or_404(
        self, session: AsyncSession, parent_id: UUID, version_id: UUID
    ) -> VersionModelT:
        """La version `version_id`, que debe pertenecer a `parent_id`."""
        version = await session.get(self.model, version_id)
        if version is None or getattr(version, self.parent_fk) != parent_id:
            raise not_found(
                "una version",
                version_id,
                scope=f" para {self._definite} '{parent_id}'",
                parent={self.parent_fk: str(parent_id)},
            )
        return version

    async def get_draft(
        self, session: AsyncSession, parent_id: UUID, version_id: UUID
    ) -> VersionModelT:
        """Como `get_or_404`, y ademas debe estar en `draft` (422 si no)."""
        version = await self.get_or_404(session, parent_id, version_id)
        self.ensure_draft(version)
        return version

    async def list_versions(
        self,
        session: AsyncSession,
        parent_id: UUID,
        pagination: PaginationParams,
        status: VersionStatus | None = None,
    ) -> Page[Any]:
        """Versiones del padre, la mas reciente primero; `status` filtra."""
        await self._parent(session, parent_id)
        stmt = select(self.model).where(
            getattr(self.model, self.parent_fk) == parent_id
        )
        if status is not None:
            stmt = stmt.where(self.model.status == status)  # type: ignore[attr-defined]
        versions, total = await paginate(
            session,
            stmt,
            pagination,
            self.model.version_number.desc(),  # type: ignore[attr-defined]
        )
        return Page[self.read_schema](  # type: ignore[name-defined]
            items=[self.read_schema.model_validate(v) for v in versions],  # type: ignore[union-attr]
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def read_version(
        self, session: AsyncSession, parent_id: UUID, version_id: UUID
    ) -> Any:
        """`XVersionRead` de una version del padre (sin commit; para auditar el
        estado previo)."""
        version = await self.get_or_404(session, parent_id, version_id)
        return self.read_schema.model_validate(version)  # type: ignore[union-attr]

    async def read_with_owner(self, session: AsyncSession, version_id: Any) -> Any:
        """Version buscada solo por su id, con su catalogo dueno embebido
        como `owner` (`VersionOwnerRead`). 404 `VersionNotFoundError` si no
        existe.
        """
        version = await session.get(self.model, version_id)
        if version is None:
            raise VersionNotFoundError(self._owner_subject, version_id)
        owner = await session.get(self.parent_model, getattr(version, self.parent_fk))
        schema = self.owner_read_schema
        data = {
            name: getattr(version, name)
            for name in schema.model_fields  # type: ignore[union-attr]
            if name != "owner"
        }
        return schema(**data, owner=VersionOwnerRead.model_validate(owner))  # type: ignore[misc]

    # --- casos de uso (hacen commit) ---

    async def create_version(
        self, session: AsyncSession, parent_id: UUID, data: BaseModel
    ) -> Any:
        """Crea un nuevo draft: clona la ultima version (publicada o retirada)
        con `data` como overrides, o crea la version 1 desde `data` si el
        padre no tiene ninguna todavia. El padre debe estar activo.
        """
        parent = await self._parent(session, parent_id)
        ensure_active(
            parent,
            subject=self._definite,
            field=self.parent_fk,
            feminine=self._feminine,
        )

        latest = (
            await session.execute(
                select(self.model)
                .where(getattr(self.model, self.parent_fk) == parent_id)
                .order_by(self.model.version_number.desc())  # type: ignore[attr-defined]
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest is None:
            missing = [f for f in self.required_fields if getattr(data, f) is None]
            if missing:
                raise VersionMissingFieldsError(missing)
            draft = self.model(
                **{self.parent_fk: parent_id}, version_number=1, **data.model_dump()
            )
            session.add(draft)
        else:
            if latest.status == DRAFT:  # type: ignore[attr-defined]
                raise VersionDraftExistsError(
                    self._definite.capitalize(), self.parent_fk, parent_id
                )
            draft = await self.create_draft(session, parent_id, latest)
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(draft, field, value)
            if self.clone_content is not None:
                await self.clone_content(session, latest.id, draft.id)  # type: ignore[attr-defined]
        return await self._commit_read(session, draft)

    async def update_version(
        self,
        session: AsyncSession,
        parent_id: UUID,
        version_id: UUID,
        data: BaseModel,
    ) -> Any:
        version = await self.get_draft(session, parent_id, version_id)
        version = await update_entity(session, version, data)
        return self.read_schema.model_validate(version)  # type: ignore[union-attr]

    async def publish_version(
        self, session: AsyncSession, parent_id: UUID, version_id: UUID
    ) -> Any:
        version = await self.get_draft(session, parent_id, version_id)
        missing = [
            field
            for field, indicator in self.publish_required.items()
            if getattr(version, indicator) is None
        ]
        if missing:
            raise VersionMissingFieldsError(missing, action="publicar la version")
        if self.validate_publish is not None:
            await self.validate_publish(session, version)
        await self.publish(session, version)
        return await self._commit_read(session, version)

    async def retire_version(
        self, session: AsyncSession, parent_id: UUID, version_id: UUID
    ) -> Any:
        """409 `version_in_use` si la usan examenes activos (ver
        `register_version_usage`)."""
        version = await self.get_or_404(session, parent_id, version_id)
        await self.retire(session, version)
        return await self._commit_read(session, version)

    async def _commit_read(self, session: AsyncSession, version: Any) -> Any:
        await session.commit()
        await session.refresh(version)
        return self.read_schema.model_validate(version)  # type: ignore[union-attr]

    # --- bajo nivel (solo add/flush) ---

    def _clonable_fields(self) -> list[str]:
        """Columnas propias del modelo (no las de ciclo de vida ni la FK al
        padre), para copiarlas al clonar un nuevo draft.
        """
        mapper = inspect(self.model)
        excluded = _NON_CLONABLE_COLUMNS | {self.parent_fk}
        return [column.key for column in mapper.columns if column.key not in excluded]

    async def create_draft(
        self,
        session: AsyncSession,
        parent_id: Any,
        source_version: VersionModelT,
    ) -> VersionModelT:
        """Clona `source_version` (la ultima version del padre, publicada o
        retirada) como nuevo draft con `version_number + 1`. No valida que
        pertenezca a `parent_id` ni que no exista ya un draft (lo hace
        `create_version`).
        """
        fields = self._clonable_fields()
        # Columnas diferidas (p. ej. un archivo base64): cargarlas aqui, en
        # async, porque un `getattr` sincrono dispararia una carga perezosa.
        unloaded = [f for f in fields if f in inspect(source_version).unloaded]
        if unloaded:
            await session.refresh(source_version, attribute_names=unloaded)
        values = {field: getattr(source_version, field) for field in fields}
        draft = self.model(
            **values,
            **{self.parent_fk: parent_id},
            version_number=source_version.version_number + 1,  # type: ignore[attr-defined]
            status=DRAFT,
            published_at=None,
            change_notes=None,
        )
        session.add(draft)
        await session.flush()
        return draft

    def ensure_draft(self, version: VersionModelT) -> None:
        """Valida que la version sea editable o publicable (solo `draft`)."""
        status = version.status  # type: ignore[attr-defined]
        if status != DRAFT:
            raise ValidationAppError(
                "Solo se puede editar o publicar una version en borrador "
                f"(estado actual: '{status}').",
                details={"status": status},
            )

    async def publish(
        self, session: AsyncSession, version: VersionModelT
    ) -> VersionModelT:
        """Fija `published_at` y pasa la version a `published`."""
        self.ensure_draft(version)
        version.status = PUBLISHED  # type: ignore[attr-defined]
        version.published_at = datetime.now(UTC)  # type: ignore[attr-defined]
        await session.flush()
        return version

    async def retire(
        self, session: AsyncSession, version: VersionModelT
    ) -> VersionModelT:
        """Retira una version `published`, salvo que el buscador de usos
        registrado para esta tabla de versiones reporte usos: 409
        `version_in_use`.
        """
        status = version.status  # type: ignore[attr-defined]
        if status != PUBLISHED:
            raise ValidationAppError(
                "Solo se puede retirar una version publicada "
                f"(estado actual: '{status}').",
                details={"status": status},
            )
        version_id = version.id  # type: ignore[attr-defined]
        finder = _version_usage_finders.get(self.model.__tablename__)  # type: ignore[attr-defined]
        if finder is not None:
            codes = sorted(set(await finder(session, version_id)))
            if codes:
                raise VersionInUseError(version_id, codes)
        version.status = RETIRED  # type: ignore[attr-defined]
        await session.flush()
        return version


# --- Usos de una version (inversion de dependencia, ver docstring) ---

# `finder(session, version_id)` -> codigos de los examenes ACTIVOS que la usan.
VersionUsageFinder = Callable[[AsyncSession, Any], Awaitable[list[str]]]

# tabla de versiones -> buscador (idempotente por tabla).
_version_usage_finders: dict[str, VersionUsageFinder] = {}


def register_version_usage(version_table: str, finder: VersionUsageFinder) -> None:
    """Registra quien usa las filas de `version_table` (codigos de examenes
    activos). Lo llama `lab_tests` al arrancar la app (`app/main.py`);
    registrar de nuevo la misma tabla reemplaza el buscador.
    """
    _version_usage_finders[version_table] = finder


class VersionInUseError(ConflictError):
    """409: no se puede retirar una version mientras examenes activos la
    usen. `details` = `{"id": <version>, "lab_test_codes": [codigos]}`."""

    code = "version_in_use"

    def __init__(self, version_id: Any, lab_test_codes: list[str]) -> None:
        super().__init__(
            message=(
                "No se puede retirar la versión: la usan exámenes activos "
                f"({', '.join(lab_test_codes)})."
            ),
            details={"id": str(version_id), "lab_test_codes": lab_test_codes},
        )
