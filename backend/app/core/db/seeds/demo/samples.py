"""Muestras y tipos de muestra (recipientes de toma).

Colores de tapa y aditivos segun el codigo internacional de tubos de
extraccion; orden de llenado segun CLSI GP41 (hemocultivo 1, citrato 2,
suero 3, heparina 4, EDTA 5, fluoruro 6). Volumenes y estabilidades son
valores tipicos de insertos de fabricantes: el laboratorio debe validarlos
contra sus proveedores.
"""

from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class SampleTypeSeed(NamedTuple):
    code: str
    name: str
    specimen: str
    cap_color_hex: str | None
    additive: str | None
    volume_ml: float | None
    storage_temperature: str | None
    stability_hours: int | None
    draw_order: int | None
    instructions: str


class SampleSeed(NamedTuple):
    code: str
    name: str
    description: str
    types: tuple[SampleTypeSeed, ...]


SAMPLES: tuple[SampleSeed, ...] = (
    SampleSeed(
        "SANGRE_VENOSA",
        "Sangre venosa",
        "Sangre obtenida por venopunción, recolectada en tubos al vacío según "
        "el análisis solicitado.",
        (
            SampleTypeSeed(
                "TUBO_ROJO",
                "Tubo tapa roja (suero, sin aditivo)",
                "suero",
                "#E53935",
                "Sin aditivo (activador de coágulo en la pared)",
                6.0,
                "2-8 °C",
                72,
                3,
                "Dejar coagular 30 minutos en posición vertical y centrifugar "
                "a 1.300 g por 10 minutos. Separar el suero antes de 2 horas.",
            ),
            SampleTypeSeed(
                "TUBO_DORADO",
                "Tubo tapa dorada (SST, activador de coágulo y gel separador)",
                "suero",
                "#FBC02D",
                "Activador de coágulo y gel separador",
                5.0,
                "2-8 °C",
                72,
                3,
                "Mezclar por inversión 5 veces, dejar coagular 30 minutos y "
                "centrifugar a 1.300 g por 10 minutos. No abrir el tubo "
                "antes de centrifugar.",
            ),
            SampleTypeSeed(
                "TUBO_LILA",
                "Tubo tapa lila (EDTA K2)",
                "sangre_total",
                "#9575CD",
                "EDTA dipotásico (K2)",
                3.0,
                "2-8 °C",
                24,
                5,
                "Llenar hasta la marca y mezclar por inversión 8 a 10 veces "
                "de inmediato para evitar coágulos.",
            ),
            SampleTypeSeed(
                "TUBO_AZUL",
                "Tubo tapa azul claro (citrato de sodio 3,2 %)",
                "plasma",
                "#4FC3F7",
                "Citrato de sodio 3,2 % (relación 1:9)",
                2.7,
                "15-25 °C",
                4,
                2,
                "Llenar exactamente hasta la marca (relación sangre/anticoagulante "
                "1:9) y mezclar suavemente por inversión 3 a 4 veces. No refrigerar.",
            ),
            SampleTypeSeed(
                "TUBO_VERDE",
                "Tubo tapa verde (heparina de litio)",
                "plasma",
                "#43A047",
                "Heparina de litio",
                4.0,
                "2-8 °C",
                24,
                4,
                "Mezclar por inversión 8 a 10 veces y centrifugar a 1.300 g "
                "por 10 minutos; separar el plasma.",
            ),
            SampleTypeSeed(
                "TUBO_GRIS",
                "Tubo tapa gris (fluoruro de sodio / oxalato de potasio)",
                "plasma",
                "#9E9E9E",
                "Fluoruro de sodio y oxalato de potasio",
                2.0,
                "15-25 °C",
                24,
                6,
                "Mezclar por inversión 8 a 10 veces. El fluoruro inhibe la "
                "glucólisis y mantiene estable la glucosa.",
            ),
        ),
    ),
    SampleSeed(
        "ORINA",
        "Orina",
        "Orina recolectada por micción espontánea (muestra aislada, chorro "
        "medio u orina de 24 horas).",
        (
            SampleTypeSeed(
                "ORINA_FRASCO",
                "Frasco de orina de boca ancha (muestra aislada)",
                "orina",
                None,
                None,
                10.0,
                "15-25 °C",
                2,
                None,
                "Primera orina de la mañana o muestra reciente. Procesar en "
                "las 2 horas siguientes; si no es posible, refrigerar hasta 24 horas.",
            ),
            SampleTypeSeed(
                "ORINA_CULTIVO",
                "Frasco estéril de orina para urocultivo (chorro medio)",
                "orina",
                None,
                None,
                10.0,
                "2-8 °C",
                24,
                None,
                "Lavado genital previo, desechar el primer chorro y recoger el "
                "medio en el frasco estéril sin tocar el borde interno. "
                "Refrigerar si no se entrega en 2 horas.",
            ),
            SampleTypeSeed(
                "ORINA_24H",
                "Recolector de orina de 24 horas",
                "orina",
                None,
                None,
                None,
                "2-8 °C",
                24,
                None,
                "Recolectar TODA la orina durante 24 horas en el galón, "
                "mantenerlo refrigerado y medir el volumen total al entregarlo.",
            ),
        ),
    ),
    SampleSeed(
        "HECES",
        "Heces",
        "Materia fecal recolectada por evacuación espontánea en recipiente limpio.",
        (
            SampleTypeSeed(
                "HECES_RECOLECTOR",
                "Recolector de heces con cucharilla",
                "heces",
                None,
                None,
                None,
                "2-8 °C",
                2,
                None,
                "Recoger una porción del tamaño de una nuez (unos 5 g) sin "
                "mezclar con orina ni agua del inodoro. Entregar en 2 horas.",
            ),
            SampleTypeSeed(
                "HECES_CULTIVO",
                "Recolector estéril o hisopo rectal en medio Cary-Blair",
                "heces",
                None,
                "Medio de transporte Cary-Blair",
                None,
                "2-8 °C",
                24,
                None,
                "Recoger en recipiente estéril o introducir el hisopo rectal "
                "y sumergirlo en el medio de transporte. Entregar el mismo día.",
            ),
            SampleTypeSeed(
                "HECES_SERIADO",
                "Recolector con conservante SAF (coproscópico seriado)",
                "heces",
                None,
                "Conservante SAF (acetato de sodio, ácido acético, formol)",
                None,
                "15-25 °C",
                None,
                None,
                "Una porción de heces en el frasco con conservante en tres "
                "días diferentes (muestras 1, 2 y 3). Mezclar bien y rotular "
                "cada frasco con el número de muestra.",
            ),
        ),
    ),
)

# Tipo descontinuado (se desactiva al final de la carga con motivo).
DISCONTINUED_SAMPLE_TYPE = SampleTypeSeed(
    "TUBO_ROJO_VIDRIO",
    "Tubo tapa roja de vidrio (sin aditivo)",
    "suero",
    "#C62828",
    "Sin aditivo",
    5.0,
    "2-8 °C",
    72,
    3,
    "Tubo de vidrio reemplazado por tubo plástico (PET).",
)
DISCONTINUED_SAMPLE_TYPE_REASON = (
    "Reemplazado por el tubo plástico PET por bioseguridad (menor riesgo de rotura)."
)


def sample_type_payload(seed: SampleTypeSeed) -> dict:
    return {
        "code": seed.code,
        "name": seed.name,
        "specimen": seed.specimen,
        "cap_color_hex": seed.cap_color_hex,
        "additive": seed.additive,
        "volume_ml": seed.volume_ml,
        "storage_temperature": seed.storage_temperature,
        "stability_hours": seed.stability_hours,
        "draw_order": seed.draw_order,
        "collection_instructions": seed.instructions,
    }


async def load(api: DemoApi, registry: Registry) -> None:
    for sample in SAMPLES:
        created = await api.post(
            "/samples",
            {
                "code": sample.code,
                "name": sample.name,
                "description": sample.description,
            },
        )
        registry.samples[sample.code] = created["id"]
        for seed in sample.types:
            sample_type = await api.post(
                f"/samples/{created['id']}/types", sample_type_payload(seed)
            )
            registry.sample_types[seed.code] = sample_type["id"]
    # Tipo que luego se desactiva: pertenece a "Sangre venosa".
    legacy = await api.post(
        f"/samples/{registry.samples['SANGRE_VENOSA']}/types",
        sample_type_payload(DISCONTINUED_SAMPLE_TYPE),
    )
    registry.sample_types[DISCONTINUED_SAMPLE_TYPE.code] = legacy["id"]
