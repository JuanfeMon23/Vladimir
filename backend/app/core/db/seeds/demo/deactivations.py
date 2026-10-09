"""Desactivaciones de demostracion (para que la pestana Actividad tenga
contenido): 3 elementos con motivo realista, ninguno referenciado por un
examen ni por una plantilla.

- Un analito descontinuado (`CKMB`).
- Un tipo de muestra reemplazado (`TUBO_ROJO_VIDRIO`).
- Un miembro del personal que se retiro (ex encargado de Hematologia).
"""

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry
from app.core.db.seeds.demo.result_templates import (
    DISCONTINUED_ANALYTE,
    DISCONTINUED_ANALYTE_REASON,
)
from app.core.db.seeds.demo.samples import (
    DISCONTINUED_SAMPLE_TYPE,
    DISCONTINUED_SAMPLE_TYPE_REASON,
)

RETIRED_STAFF_DOCUMENT = "71654309"  # Carlos Eduardo Londono Velez
RETIRED_STAFF_REASON = (
    "Retiro voluntario del laboratorio; entregó la jefatura de Hematología."
)

# (ruta del recurso, clave del registro) por desactivacion, en orden.
DEACTIVATIONS = (
    ("/analytes", "analytes", DISCONTINUED_ANALYTE, DISCONTINUED_ANALYTE_REASON),
    (
        "/sample-types",
        "sample_types",
        DISCONTINUED_SAMPLE_TYPE.code,
        DISCONTINUED_SAMPLE_TYPE_REASON,
    ),
    ("/staff", "staff", RETIRED_STAFF_DOCUMENT, RETIRED_STAFF_REASON),
)


async def load(api: DemoApi, registry: Registry) -> None:
    for path, registry_key, key, reason in DEACTIVATIONS:
        entity_id = getattr(registry, registry_key)[key]
        await api.patch(
            f"{path}/{entity_id}", {"is_active": False, "activity_reason": reason}
        )
