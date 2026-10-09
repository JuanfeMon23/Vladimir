"""Etiquetas de impresion (version 1 publicada).

ZPL para impresoras termicas Zebra de 203 dpi (8 puntos/mm) y un rotulo HTML
para impresora comun. Los `{{placeholders}}` los reemplaza la aplicacion que
imprime; su significado esta en el campo `placeholders` de cada version.
"""

from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry

PLACEHOLDERS = {
    "patient_name": "Nombre completo del paciente",
    "patient_document": "Documento de identidad del paciente",
    "accession_number": "Número de orden / muestra (se imprime también como código de barras)",
    "barcode": "Valor codificado en el código de barras",
    "test_codes": "Códigos de los exámenes solicitados",
    "sample_type": "Tipo de muestra / recipiente",
    "collected_at": "Fecha y hora de la toma",
    "area": "Área del laboratorio que procesa la muestra",
}


class LabelSeed(NamedTuple):
    code: str
    name: str
    description: str
    width_mm: float
    height_mm: float
    dpi: int
    output_format: str
    barcode_type: str
    copies: int
    template_content: str
    placeholders: tuple[str, ...]


_ZPL_TUBO = """^XA
^CI28
^PW400
^LL200
^FO16,10^A0N,26,26^FD{{patient_name}}^FS
^FO16,40^A0N,22,22^FDDoc: {{patient_document}}^FS
^FO16,68^BY2,3,64^BCN,64,N,N,N^FD{{barcode}}^FS
^FO16,140^A0N,22,22^FD{{accession_number}}^FS
^FO16,168^A0N,20,20^FD{{sample_type}}  {{collected_at}}^FS
^PQ1
^XZ"""

_ZPL_FRASCO = """^XA
^CI28
^PW480
^LL240
^FO20,12^A0N,28,28^FD{{patient_name}}^FS
^FO20,46^A0N,24,24^FDDoc: {{patient_document}}^FS
^FO20,78^BY2,3,70^BCN,70,N,N,N^FD{{barcode}}^FS
^FO20,158^A0N,24,24^FD{{accession_number}}^FS
^FO20,188^A0N,22,22^FD{{sample_type}}  {{collected_at}}^FS
^FO330,158^A0N,22,22^FD{{area}}^FS
^PQ1
^XZ"""

_ZPL_ALICUOTA = """^XA
^CI28
^PW240
^LL120
^FO12,8^BXN,4,200^FD{{barcode}}^FS
^FO96,10^A0N,20,20^FD{{accession_number}}^FS
^FO96,38^A0N,18,18^FD{{sample_type}}^FS
^FO96,62^A0N,18,18^FD{{collected_at}}^FS
^PQ1
^XZ"""

_HTML_ORDEN = """<div style="width:100mm;height:50mm;font-family:Arial,sans-serif;font-size:10pt;padding:3mm;box-sizing:border-box">
  <div style="font-size:12pt;font-weight:bold">{{patient_name}}</div>
  <div>Documento: {{patient_document}}</div>
  <div>Orden: <strong>{{accession_number}}</strong></div>
  <div>Área: {{area}}</div>
  <div>Exámenes: {{test_codes}}</div>
  <div>Muestra: {{sample_type}} &middot; Toma: {{collected_at}}</div>
  <svg class="barcode" data-value="{{barcode}}" data-format="code128"></svg>
</div>"""

LABELS: tuple[LabelSeed, ...] = (
    LabelSeed(
        "ETQ_TUBO",
        "Etiqueta de tubo con código de barras",
        "Etiqueta de 50 x 25 mm para tubos de extracción: paciente, documento, "
        "código de barras Code 128, número de orden, muestra y fecha de toma.",
        50,
        25,
        203,
        "zpl",
        "code128",
        1,
        _ZPL_TUBO,
        (
            "patient_name",
            "patient_document",
            "barcode",
            "accession_number",
            "sample_type",
            "collected_at",
        ),
    ),
    LabelSeed(
        "ETQ_FRASCO",
        "Etiqueta de frasco de orina y heces",
        "Etiqueta de 60 x 30 mm para frascos y recolectores de orina o heces, "
        "con el área que procesa la muestra.",
        60,
        30,
        203,
        "zpl",
        "code128",
        1,
        _ZPL_FRASCO,
        (
            "patient_name",
            "patient_document",
            "barcode",
            "accession_number",
            "sample_type",
            "collected_at",
            "area",
        ),
    ),
    LabelSeed(
        "ETQ_ALICUOTA",
        "Etiqueta de alícuota (criotubo)",
        "Etiqueta pequeña de 30 x 15 mm con código DataMatrix para alícuotas "
        "de suero que se almacenan (serología y confirmatorios).",
        30,
        15,
        203,
        "zpl",
        "datamatrix",
        2,
        _ZPL_ALICUOTA,
        ("barcode", "accession_number", "sample_type", "collected_at"),
    ),
    LabelSeed(
        "ETQ_ORDEN",
        "Rótulo de orden de servicio",
        "Rótulo HTML de 100 x 50 mm para impresora de oficina, con los datos "
        "del paciente, el área y los exámenes de la orden (cultivos).",
        100,
        50,
        203,
        "html",
        "code128",
        1,
        _HTML_ORDEN,
        (
            "patient_name",
            "patient_document",
            "accession_number",
            "area",
            "test_codes",
            "sample_type",
            "collected_at",
            "barcode",
        ),
    ),
)


async def load(api: DemoApi, registry: Registry) -> None:
    for label in LABELS:
        created = await api.post(
            "/print-labels",
            {"code": label.code, "name": label.name, "description": label.description},
        )
        registry.labels[label.code] = created["id"]
        version = await api.post(
            f"/print-labels/{created['id']}/versions",
            {
                "width_mm": label.width_mm,
                "height_mm": label.height_mm,
                "dpi": label.dpi,
                "output_format": label.output_format,
                "barcode_type": label.barcode_type,
                "copies": label.copies,
                "template_content": label.template_content,
                "placeholders": {key: PLACEHOLDERS[key] for key in label.placeholders},
                "change_notes": "Versión inicial.",
            },
        )
        published = await api.post(
            f"/print-labels/{created['id']}/versions/{version['id']}/publish"
        )
        registry.label_versions[label.code] = published["id"]
