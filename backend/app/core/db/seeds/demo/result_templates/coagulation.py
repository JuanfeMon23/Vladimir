"""Coagulacion: TP / INR, TTP y fibrinogeno.

Valores de referencia de ADULTOS (Mayo Clinic Laboratories). TP y TTP
dependen del reactivo y del coagulometro: el laboratorio debe usar los
rangos de su plataforma. El INR se reporta directamente (su calculo exige un
exponente: (TP/TP normal medio)^ISI, que la gramatica de formulas no admite).
La relacion paciente/control SI se calcula. A validar con el laboratorio.
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
    AnalyteSpec("TP", "Tiempo de protrombina (TP)", "s", "5902-2"),
    AnalyteSpec("TP_CONTROL", "Tiempo de protrombina, control", "s"),
    AnalyteSpec("INR", "INR", "{ratio}", "6301-6"),
    AnalyteSpec(
        "TP_RELACION",
        "Relación TP paciente/control",
        "{ratio}",
        description="Calculada: TP / TP control.",
    ),
    AnalyteSpec("TTP", "Tiempo parcial de tromboplastina (TTP)", "s", "3173-2"),
    AnalyteSpec("TTP_CONTROL", "Tiempo parcial de tromboplastina, control", "s"),
    AnalyteSpec(
        "TTP_RELACION",
        "Relación TTP paciente/control",
        "{ratio}",
        description="Calculada: TTP / TTP control.",
    ),
    AnalyteSpec("FIBRINOGENO", "Fibrinógeno (Clauss)", "mg/dL", "3255-7"),
)

TP_INR = TemplateSpec(
    "TP_INR",
    "Tiempo de protrombina e INR",
    "TP con control, relación e INR. El INR es el parámetro de seguimiento de "
    "la terapia con warfarina (rango terapéutico habitual 2,0-3,0).",
    (
        SectionSpec(
            "Tiempo de protrombina",
            (
                num("TP", "s", 1, between(11.0, 13.5)),
                num("TP_CONTROL", "s", 1, reportable=False),
                calc("TP_RELACION", "{ratio}", 2, "TP / TP_CONTROL", between(0.8, 1.2)),
                num(
                    "INR",
                    "{ratio}",
                    2,
                    between(
                        0.8,
                        1.2,
                        critical_high=5.0,
                        interpretation="En terapia con warfarina el rango "
                        "terapéutico habitual es 2,0 - 3,0 (3,0 - 4,0 con "
                        "válvula mecánica).",
                    ),
                ),
            ),
        ),
    ),
)

TTP = TemplateSpec(
    "TTP",
    "Tiempo parcial de tromboplastina (TTP)",
    "TTP activado con control y relación paciente/control.",
    (
        SectionSpec(
            "Tiempo parcial de tromboplastina",
            (
                num(
                    "TTP",
                    "s",
                    1,
                    between(25.0, 35.0, critical_high=100.0),
                ),
                num("TTP_CONTROL", "s", 1, reportable=False),
                calc(
                    "TTP_RELACION", "{ratio}", 2, "TTP / TTP_CONTROL", between(0.8, 1.2)
                ),
            ),
        ),
    ),
)

FIBRINOGENO = TemplateSpec(
    "FIBRINOGENO",
    "Fibrinógeno",
    "Fibrinógeno funcional por el método de Clauss.",
    (
        SectionSpec(
            "Fibrinógeno",
            (
                num(
                    "FIBRINOGENO", "mg/dL", 0, between(200.0, 400.0, critical_low=100.0)
                ),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (TP_INR, TTP, FIBRINOGENO)
