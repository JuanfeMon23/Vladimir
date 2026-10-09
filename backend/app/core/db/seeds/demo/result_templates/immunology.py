"""Inmunologia y serologia: VIH, sifilis, hepatitis B y C, PCR, factor
reumatoide, grupo sanguineo y Rh, y prueba de embarazo en orina.

Resultados cualitativos con el conjunto `reactividad` (reactivo / no
reactivo / indeterminado) o `positividad`; titulacion de VDRL con el conjunto
`titulos`. Valores de referencia de adultos (Mayo Clinic Laboratories) para
PCR y factor reumatoide; dependen del metodo. A validar con el laboratorio.
Un resultado reactivo de tamizacion requiere prueba confirmatoria.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    RangeSpec,
    SectionSpec,
    TemplateSpec,
    below,
    num,
    opt,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec(
        "VIH",
        "VIH 1/2 antígeno/anticuerpo (4.ª generación)",
        description="Tamización de VIH-1/2 y antígeno p24 por inmunoensayo.",
    ),
    AnalyteSpec(
        "VDRL_REACT", "VDRL/RPR (reactividad)", description="Prueba no treponémica."
    ),
    AnalyteSpec(
        "VDRL_TITULO", "VDRL/RPR (título)", description="Dilución de la titulación."
    ),
    AnalyteSpec("HBSAG", "Antígeno de superficie de hepatitis B (HBsAg)"),
    AnalyteSpec("ANTI_HCV", "Anticuerpos contra hepatitis C (anti-HCV)"),
    AnalyteSpec("PCR", "Proteína C reactiva cuantitativa", "mg/L", "1988-5"),
    AnalyteSpec("FR", "Factor reumatoide", "[IU]/mL", "11572-5"),
    AnalyteSpec("GRUPO_ABO", "Grupo sanguíneo ABO", loinc="883-9"),
    AnalyteSpec("FACTOR_RH", "Factor Rh (D)", loinc="10331-7"),
    AnalyteSpec(
        "EMBARAZO_ORINA",
        "Prueba de embarazo en orina (hCG)",
        loinc="2106-3",
        description="Detección cualitativa de hCG en orina.",
    ),
)

_NO_REACTIVO = RangeSpec(option="no_reactivo", text="No reactivo")

VIH = TemplateSpec(
    "VIH",
    "VIH 1/2 antígeno/anticuerpo",
    "Prueba de tamización de 4.ª generación. Todo resultado reactivo debe "
    "confirmarse según el algoritmo vigente.",
    (SectionSpec("Serología", (opt("VIH", "reactividad", _NO_REACTIVO),)),),
)

VDRL = TemplateSpec(
    "VDRL",
    "VDRL / RPR",
    "Prueba no treponémica para sífilis, con titulación si es reactiva.",
    (
        SectionSpec(
            "Serología",
            (
                opt("VDRL_REACT", "reactividad", _NO_REACTIVO),
                opt(
                    "VDRL_TITULO",
                    "titulos",
                    _NO_REACTIVO,
                    result_type="titer",
                    required=False,
                ),
            ),
        ),
    ),
)

HBSAG = TemplateSpec(
    "HBSAG",
    "Antígeno de superficie de hepatitis B (HBsAg)",
    "Tamización de infección por el virus de la hepatitis B.",
    (SectionSpec("Serología", (opt("HBSAG", "reactividad", _NO_REACTIVO),)),),
)

ANTI_HCV = TemplateSpec(
    "ANTI_HCV",
    "Anticuerpos anti-hepatitis C (anti-HCV)",
    "Tamización de infección por el virus de la hepatitis C.",
    (SectionSpec("Serología", (opt("ANTI_HCV", "reactividad", _NO_REACTIVO),)),),
)

PCR = TemplateSpec(
    "PCR",
    "Proteína C reactiva cuantitativa",
    "Marcador de inflamación aguda por inmunoturbidimetría.",
    (
        SectionSpec(
            "Marcador inflamatorio",
            (num("PCR", "mg/L", 1, below(5.0, "< 5,0 mg/L")),),
        ),
    ),
)

FACTOR_REUMATOIDE = TemplateSpec(
    "FACTOR_REUMATOIDE",
    "Factor reumatoide",
    "Factor reumatoide cuantitativo por inmunoturbidimetría.",
    (
        SectionSpec(
            "Autoinmunidad",
            (num("FR", "[IU]/mL", 0, below(14.0, "< 14 UI/mL")),),
        ),
    ),
)

GRUPO_RH = TemplateSpec(
    "GRUPO_RH",
    "Grupo sanguíneo y Rh",
    "Grupo ABO y factor Rh (D).",
    (
        SectionSpec(
            "Inmunohematología",
            (opt("GRUPO_ABO", "grupo_abo"), opt("FACTOR_RH", "factor_rh")),
        ),
    ),
)

EMBARAZO_ORINA = TemplateSpec(
    "EMBARAZO_ORINA",
    "Prueba de embarazo en orina",
    "Detección cualitativa de hCG en orina por inmunocromatografía.",
    (
        SectionSpec(
            "Embarazo",
            (
                opt(
                    "EMBARAZO_ORINA",
                    "positividad",
                    RangeSpec(option="negativo", text="Negativo"),
                ),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (
    VIH,
    VDRL,
    HBSAG,
    ANTI_HCV,
    PCR,
    FACTOR_REUMATOIDE,
    GRUPO_RH,
    EMBARAZO_ORINA,
)
