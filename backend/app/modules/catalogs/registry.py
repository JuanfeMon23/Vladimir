"""Los 9 catalogos de categoria expuestos por la API y como se publican.

Cada entrada liga el `slug` de la ruta (`/api/v1/catalogs/<slug>`) con su
modelo (propiedad del modulo que lo usa; se importa por su `__init__`) y sus
schemas. Agregar un catalogo = una entrada aqui; las rutas, la auditoria y la
tabla de `ACTIVATABLE_TABLES` salen del patron comun.
"""

from dataclasses import dataclass

from app.modules.catalogs import schemas
from app.modules.consent_documents import ConsentDocumentType, ConsentSigner
from app.modules.preconditions import (
    DurationUnit,
    PreconditionCategory,
    PreconditionKind,
)
from app.modules.result_templates import AgeUnit, ResultType, Sex
from app.modules.samples import SpecimenType


@dataclass(frozen=True)
class CatalogSpec:
    slug: str
    model: type
    read: type[schemas.CategoryRead]
    create: type[schemas.CategoryCreate]
    update: type[schemas.CategoryUpdate]
    # Con articulo indefinido, para los mensajes ("Ya existe un sexo ...").
    noun: str
    # (columna booleana, mensaje) si a lo sumo una fila puede tenerla en `true`
    # (indice unico parcial); `{code}` es el codigo de la fila que ya la tiene.
    exclusive_flag: tuple[str, str] | None = None

    @property
    def entity(self) -> str:
        """Nombre de la tabla (= `entity_type` de auditoria y de `/activity`)."""
        return self.model.__tablename__  # type: ignore[attr-defined]


CATALOGS: tuple[CatalogSpec, ...] = (
    CatalogSpec(
        "consent-document-types",
        ConsentDocumentType,
        schemas.CategoryRead,
        schemas.CategoryCreate,
        schemas.CategoryUpdate,
        "un tipo de documento de consentimiento",
    ),
    CatalogSpec(
        "consent-signers",
        ConsentSigner,
        schemas.CategoryRead,
        schemas.CategoryCreate,
        schemas.CategoryUpdate,
        "un firmante",
    ),
    CatalogSpec(
        "duration-units",
        DurationUnit,
        schemas.DurationUnitRead,
        schemas.DurationUnitCreate,
        schemas.DurationUnitUpdate,
        "una unidad de duración",
    ),
    CatalogSpec(
        "precondition-kinds",
        PreconditionKind,
        schemas.CategoryRead,
        schemas.CategoryCreate,
        schemas.CategoryUpdate,
        "un tipo de precondición",
    ),
    CatalogSpec(
        "precondition-categories",
        PreconditionCategory,
        schemas.CategoryRead,
        schemas.CategoryCreate,
        schemas.CategoryUpdate,
        "una categoría de precondición",
    ),
    CatalogSpec(
        "specimen-types",
        SpecimenType,
        schemas.CategoryRead,
        schemas.CategoryCreate,
        schemas.CategoryUpdate,
        "un espécimen",
    ),
    CatalogSpec(
        "result-types",
        ResultType,
        schemas.ResultTypeRead,
        schemas.ResultTypeCreate,
        schemas.ResultTypeUpdate,
        "un tipo de resultado",
    ),
    CatalogSpec(
        "sexes",
        Sex,
        schemas.SexRead,
        schemas.SexCreate,
        schemas.SexUpdate,
        "un sexo",
        exclusive_flag=(
            "is_wildcard",
            "Ya existe un sexo comodín ({code}); solo puede haber uno.",
        ),
    ),
    CatalogSpec(
        "age-units",
        AgeUnit,
        schemas.AgeUnitRead,
        schemas.AgeUnitCreate,
        schemas.AgeUnitUpdate,
        "una unidad de edad",
    ),
)
