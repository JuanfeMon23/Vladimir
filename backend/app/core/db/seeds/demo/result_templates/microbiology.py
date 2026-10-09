"""Microbiologia: urocultivo y coprocultivo con antibiograma sencillo.

Resultado del cultivo y microorganismo aislado como texto libre; recuento de
colonias del urocultivo numerico (UFC/mL); antibiograma por difusion en disco
(Kirby-Bauer) interpretado como sensible / intermedio / resistente segun los
puntos de corte del laboratorio (CLSI). Los antibioticos del panel se
reutilizan entre ambas plantillas. A validar con el laboratorio.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    SectionSpec,
    TemplateSpec,
    below,
    num,
    opt,
    text,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec("URO_RESULTADO", "Resultado del urocultivo"),
    AnalyteSpec("URO_RECUENTO", "Recuento de colonias en orina", "[CFU]/mL"),
    AnalyteSpec("URO_MICROORGANISMO", "Microorganismo aislado en orina"),
    AnalyteSpec("COPC_RESULTADO", "Resultado del coprocultivo"),
    AnalyteSpec("COPC_MICROORGANISMO", "Microorganismo aislado en heces"),
    AnalyteSpec("AB_AMP", "Ampicilina"),
    AnalyteSpec("AB_CIP", "Ciprofloxacino"),
    AnalyteSpec("AB_SXT", "Trimetoprim-sulfametoxazol"),
    AnalyteSpec("AB_NIT", "Nitrofurantoína"),
    AnalyteSpec("AB_GEN", "Gentamicina"),
    AnalyteSpec("AB_CRO", "Ceftriaxona"),
    AnalyteSpec("AB_AZM", "Azitromicina"),
)


def _antibiogram(*codes: str):
    return tuple(opt(code, "sensibilidad", required=False) for code in codes)


UROCULTIVO = TemplateSpec(
    "UROCULTIVO",
    "Urocultivo con antibiograma",
    "Cultivo cuantitativo de orina, identificación del microorganismo y antibiograma.",
    (
        SectionSpec(
            "Cultivo",
            (
                text(
                    "URO_RESULTADO",
                    required=True,
                    default="Sin crecimiento bacteriano a las 48 horas de incubación",
                ),
                num(
                    "URO_RECUENTO",
                    "[CFU]/mL",
                    0,
                    below(10000.0, "< 10.000 UFC/mL (no significativo)"),
                    required=False,
                ),
                text("URO_MICROORGANISMO"),
            ),
        ),
        SectionSpec(
            "Antibiograma (Kirby-Bauer)",
            _antibiogram("AB_AMP", "AB_CIP", "AB_SXT", "AB_NIT", "AB_GEN", "AB_CRO"),
        ),
    ),
)

COPROCULTIVO = TemplateSpec(
    "COPROCULTIVO",
    "Coprocultivo con antibiograma",
    "Cultivo de heces para patógenos entéricos (Salmonella, Shigella, "
    "Campylobacter y E. coli enteropatógena) y antibiograma del aislamiento.",
    (
        SectionSpec(
            "Cultivo",
            (
                text(
                    "COPC_RESULTADO",
                    required=True,
                    default="Sin crecimiento de Salmonella, Shigella ni Campylobacter",
                ),
                text("COPC_MICROORGANISMO"),
            ),
        ),
        SectionSpec(
            "Antibiograma (Kirby-Bauer)",
            _antibiogram("AB_AMP", "AB_CIP", "AB_SXT", "AB_CRO", "AB_AZM"),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (UROCULTIVO, COPROCULTIVO)
