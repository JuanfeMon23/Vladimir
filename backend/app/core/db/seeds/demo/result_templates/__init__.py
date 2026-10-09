"""Plantillas de resultados de la demostracion: analitos, unidades y
conjuntos extra, plantillas con secciones, analitos y rangos, publicadas
(version 1) por el flujo normal de la API.

Datos por area en `hematology.py`, `chemistry.py`, `endocrine.py`,
`immunology.py`, `urinalysis.py`, `coagulation.py`, `parasitology.py` y
`microbiology.py`; aqui solo se agregan y se cargan.
"""

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry
from app.core.db.seeds.demo.result_templates import (
    chemistry,
    coagulation,
    endocrine,
    hematology,
    immunology,
    microbiology,
    parasitology,
    urinalysis,
)
from app.core.db.seeds.demo.result_templates.catalogs import (
    EXTRA_OPTION_SETS,
    EXTRA_UNITS,
)
from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    FieldSpec,
    RangeSpec,
    TemplateSpec,
)

_MODULES = (
    hematology,
    chemistry,
    endocrine,
    immunology,
    urinalysis,
    coagulation,
    parasitology,
    microbiology,
)

ANALYTES: tuple[AnalyteSpec, ...] = tuple(a for m in _MODULES for a in m.ANALYTES)
TEMPLATES: tuple[TemplateSpec, ...] = tuple(t for m in _MODULES for t in m.TEMPLATES)

# Analito que se desactiva al final de la carga (no esta en ninguna plantilla).
DISCONTINUED_ANALYTE = "CKMB"
DISCONTINUED_ANALYTE_REASON = (
    "Prueba retirada del portafolio: el laboratorio dejó de procesar CK-MB en la sede."
)

CHANGE_NOTES = "Versión inicial."


async def _load_catalogs(api: DemoApi, registry: Registry) -> None:
    for unit in await api.get_all("/units"):
        registry.units[unit["code"]] = unit["id"]
    for unit in EXTRA_UNITS:
        created = await api.post("/units", unit._asdict())
        registry.units[unit.code] = created["id"]

    for option_set in await api.get_all("/result-option-sets"):
        registry.option_sets[option_set["code"]] = option_set["id"]
        for option in await api.get_all(
            f"/result-option-sets/{option_set['id']}/options"
        ):
            registry.options[(option_set["code"], option["code"])] = option["id"]
    for option_set in EXTRA_OPTION_SETS:
        created = await api.post(
            "/result-option-sets", {"code": option_set.code, "name": option_set.name}
        )
        registry.option_sets[option_set.code] = created["id"]
        for sort_order, option in enumerate(option_set.options, start=1):
            created_option = await api.post(
                f"/result-option-sets/{created['id']}/options",
                {
                    "code": option.code,
                    "label": option.label,
                    "sort_order": sort_order,
                    "is_abnormal": option.is_abnormal,
                },
            )
            registry.options[(option_set.code, option.code)] = created_option["id"]


async def _load_analytes(api: DemoApi, registry: Registry) -> None:
    for analyte in ANALYTES:
        created = await api.post(
            "/analytes",
            {
                "code": analyte.code,
                "name": analyte.name,
                "loinc_code": analyte.loinc,
                "default_unit_id": registry.units[analyte.unit]
                if analyte.unit
                else None,
                "description": analyte.description,
            },
        )
        registry.analytes[analyte.code] = created["id"]


def range_payload(spec: RangeSpec, field: FieldSpec, registry: Registry) -> dict:
    option_id = None
    if spec.option is not None:
        assert field.option_set is not None
        option_id = registry.options[(field.option_set, spec.option)]
    return {
        "sex": spec.sex,
        "age_min": spec.age_min,
        "age_max": spec.age_max,
        "age_unit": spec.age_unit,
        "condition": spec.condition,
        "low": spec.low,
        "high": spec.high,
        "critical_low": spec.critical_low,
        "critical_high": spec.critical_high,
        "expected_option_id": option_id,
        "expected_boolean": spec.boolean,
        "display_text": spec.text,
        "interpretation": spec.interpretation,
    }


async def _load_template(api: DemoApi, registry: Registry, spec: TemplateSpec) -> None:
    template = await api.post(
        "/result-templates",
        {"code": spec.code, "name": spec.name, "description": spec.description},
    )
    registry.templates[spec.code] = template["id"]
    base = f"/result-templates/{template['id']}"
    version = await api.post(
        f"{base}/versions",
        {
            "report_settings": {**spec.report_settings, "flag_abnormal": True},
            "change_notes": CHANGE_NOTES,
        },
    )
    version_path = f"{base}/versions/{version['id']}"

    section_ids: dict[str, str] = {}
    positions: list[tuple[str, FieldSpec, int]] = []
    sort_order = 0
    for section_order, section in enumerate(spec.sections, start=1):
        created = await api.post(
            f"{version_path}/sections",
            {"name": section.name, "sort_order": section_order},
        )
        section_ids[section.name] = created["id"]
        for field in section.fields:
            sort_order += 1
            positions.append((section.name, field, sort_order))

    # Un calculado solo puede referirse a analitos que ya esten en la version:
    # primero los que no son calculados, luego los calculados en orden.
    ordered = [p for p in positions if p[1].formula is None]
    ordered += [p for p in positions if p[1].formula is not None]
    for section_name, field, order in ordered:
        created = await api.post(
            f"{version_path}/analytes",
            {
                "section_id": section_ids[section_name],
                "analyte_id": registry.analytes[field.analyte],
                "sort_order": order,
                "result_type": field.result_type,
                "unit_id": registry.units[field.unit] if field.unit else None,
                "decimals": field.decimals,
                "option_set_id": registry.option_sets[field.option_set]
                if field.option_set
                else None,
                "formula": field.formula,
                "is_required": field.required,
                "is_reportable": field.reportable,
                "default_value": field.default,
            },
        )
        for range_spec in field.ranges:
            await api.post(
                f"{version_path}/analytes/{created['id']}/reference-ranges",
                range_payload(range_spec, field, registry),
            )

    published = await api.post(f"{version_path}/publish")
    registry.template_versions[spec.code] = published["id"]


async def load(api: DemoApi, registry: Registry) -> None:
    await _load_catalogs(api, registry)
    await _load_analytes(api, registry)
    for spec in TEMPLATES:
        await _load_template(api, registry, spec)
