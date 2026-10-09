"""Hematologia: hemograma completo.

Valores de referencia de ADULTOS (>= 18 anos) tipicos de analizadores
hematologicos automatizados (Mayo Clinic Laboratories / insertos de
fabricante); rangos por sexo en serie roja. Indices eritrocitarios y
diferencial absoluto como CALCULADOS (formulas estandar). A validar con el
laboratorio segun su equipo y su poblacion.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    SectionSpec,
    TemplateSpec,
    between,
    calc,
    num,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec("HB", "Hemoglobina", "g/dL", "718-7"),
    AnalyteSpec("HTO", "Hematocrito", "%", "4544-3"),
    AnalyteSpec("GR", "Recuento de eritrocitos", "10*6/uL", "789-8"),
    AnalyteSpec(
        "VCM",
        "Volumen corpuscular medio (VCM)",
        "fL",
        "787-2",
        "Calculado: Hto x 10 / eritrocitos.",
    ),
    AnalyteSpec(
        "HCM",
        "Hemoglobina corpuscular media (HCM)",
        "pg",
        "785-6",
        "Calculada: Hb x 10 / eritrocitos.",
    ),
    AnalyteSpec(
        "CHCM",
        "Concentración de hemoglobina corpuscular media (CHCM)",
        "g/dL",
        "786-4",
        "Calculada: Hb x 100 / Hto.",
    ),
    AnalyteSpec("RDW", "Ancho de distribución eritrocitaria (RDW-CV)", "%", "788-0"),
    AnalyteSpec("LEU", "Recuento de leucocitos", "10*3/uL", "6690-2"),
    AnalyteSpec("NEUT_PCT", "Neutrófilos (%)", "%", "770-8"),
    AnalyteSpec("LINF_PCT", "Linfocitos (%)", "%", "736-9"),
    AnalyteSpec("MONO_PCT", "Monocitos (%)", "%", "5905-5"),
    AnalyteSpec("EOS_PCT", "Eosinófilos (%)", "%", "713-8"),
    AnalyteSpec("BASO_PCT", "Basófilos (%)", "%", "706-2"),
    AnalyteSpec("NEUT_ABS", "Neutrófilos absolutos", "10*3/uL", "751-8"),
    AnalyteSpec("LINF_ABS", "Linfocitos absolutos", "10*3/uL", "731-0"),
    AnalyteSpec("MONO_ABS", "Monocitos absolutos", "10*3/uL", "742-7"),
    AnalyteSpec("EOS_ABS", "Eosinófilos absolutos", "10*3/uL", "711-2"),
    AnalyteSpec("BASO_ABS", "Basófilos absolutos", "10*3/uL", "704-7"),
    AnalyteSpec("PLT", "Recuento de plaquetas", "10*3/uL", "777-3"),
    AnalyteSpec("VPM", "Volumen plaquetario medio (VPM)", "fL", "32623-1"),
)

HEMOGRAMA = TemplateSpec(
    "HEMOGRAMA",
    "Hemograma completo",
    "Serie roja, serie blanca con diferencial (porcentaje y absolutos) y "
    "plaquetas. Valores de referencia de adultos.",
    (
        SectionSpec(
            "Serie roja",
            (
                num(
                    "HB",
                    "g/dL",
                    1,
                    between(
                        13.5, 17.5, sex="male", critical_low=7.0, critical_high=20.0
                    ),
                    between(
                        12.0, 15.5, sex="female", critical_low=7.0, critical_high=20.0
                    ),
                ),
                num(
                    "HTO",
                    "%",
                    1,
                    between(
                        41.0, 53.0, sex="male", critical_low=21.0, critical_high=60.0
                    ),
                    between(
                        36.0, 46.0, sex="female", critical_low=21.0, critical_high=60.0
                    ),
                ),
                num(
                    "GR",
                    "10*6/uL",
                    2,
                    between(4.5, 5.9, sex="male"),
                    between(4.1, 5.1, sex="female"),
                ),
                calc("VCM", "fL", 1, "HTO * 10 / GR", between(80.0, 100.0)),
                calc("HCM", "pg", 1, "HB * 10 / GR", between(27.0, 33.0)),
                calc("CHCM", "g/dL", 1, "HB * 100 / HTO", between(32.0, 36.0)),
                num("RDW", "%", 1, between(11.5, 14.5)),
            ),
        ),
        SectionSpec(
            "Serie blanca",
            (
                num(
                    "LEU",
                    "10*3/uL",
                    2,
                    between(4.5, 11.0, critical_low=2.0, critical_high=30.0),
                ),
            ),
        ),
        SectionSpec(
            "Diferencial (porcentaje)",
            (
                num("NEUT_PCT", "%", 1, between(40.0, 70.0)),
                num("LINF_PCT", "%", 1, between(20.0, 45.0)),
                num("MONO_PCT", "%", 1, between(2.0, 10.0)),
                num("EOS_PCT", "%", 1, between(1.0, 6.0)),
                num("BASO_PCT", "%", 1, between(0.0, 1.0)),
            ),
        ),
        SectionSpec(
            "Diferencial (absolutos)",
            (
                calc(
                    "NEUT_ABS",
                    "10*3/uL",
                    2,
                    "LEU * NEUT_PCT / 100",
                    between(1.8, 7.7),
                ),
                calc(
                    "LINF_ABS",
                    "10*3/uL",
                    2,
                    "LEU * LINF_PCT / 100",
                    between(1.0, 4.8),
                ),
                calc(
                    "MONO_ABS",
                    "10*3/uL",
                    2,
                    "LEU * MONO_PCT / 100",
                    between(0.1, 1.0),
                ),
                calc("EOS_ABS", "10*3/uL", 2, "LEU * EOS_PCT / 100", between(0.0, 0.5)),
                calc(
                    "BASO_ABS", "10*3/uL", 2, "LEU * BASO_PCT / 100", between(0.0, 0.2)
                ),
            ),
        ),
        SectionSpec(
            "Plaquetas",
            (
                num(
                    "PLT",
                    "10*3/uL",
                    0,
                    between(150.0, 450.0, critical_low=50.0, critical_high=1000.0),
                ),
                num("VPM", "fL", 1, between(7.5, 11.5)),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (HEMOGRAMA,)
