"""Uroanalisis completo y proteinuria de 24 horas.

Examen fisico (color y aspecto como opciones, densidad, pH), quimico por tira
reactiva en cruces (negativo, trazas, +...) y sedimento urinario (recuentos
por campo de alto poder 40x y de bajo poder 10x; elementos semicuantitativos
como ausentes/escasas/moderadas/abundantes). Valores de referencia de
adultos de uso comun (Mayo Clinic Laboratories; densidad 1,005-1,030, pH
5,0-8,0). A validar con el laboratorio segun su tira reactiva.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    RangeSpec,
    SectionSpec,
    TemplateSpec,
    below,
    between,
    calc,
    num,
    opt,
    text,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec("ORI_COLOR", "Color de la orina"),
    AnalyteSpec("ORI_ASPECTO", "Aspecto de la orina"),
    AnalyteSpec("ORI_DENSIDAD", "Densidad urinaria", "{ratio}", "5811-5"),
    AnalyteSpec("ORI_PH", "pH urinario", "[pH]", "5803-2"),
    AnalyteSpec("ORI_PROTEINAS", "Proteínas (tira reactiva)"),
    AnalyteSpec("ORI_GLUCOSA", "Glucosa (tira reactiva)"),
    AnalyteSpec("ORI_CETONAS", "Cetonas (tira reactiva)"),
    AnalyteSpec("ORI_SANGRE", "Sangre / hemoglobina (tira reactiva)"),
    AnalyteSpec("ORI_BILIRRUBINA", "Bilirrubina (tira reactiva)"),
    AnalyteSpec("ORI_UROBILINOGENO", "Urobilinógeno (tira reactiva)"),
    AnalyteSpec("ORI_NITRITOS", "Nitritos (tira reactiva)"),
    AnalyteSpec("ORI_LEUCOCITOS_ESTERASA", "Esterasa leucocitaria (tira reactiva)"),
    AnalyteSpec("SED_LEUCOCITOS", "Leucocitos en sedimento", "/[HPF]"),
    AnalyteSpec("SED_ERITROCITOS", "Eritrocitos en sedimento", "/[HPF]"),
    AnalyteSpec("SED_CEL_EPITELIALES", "Células epiteliales"),
    AnalyteSpec("SED_BACTERIAS", "Bacterias"),
    AnalyteSpec("SED_LEVADURAS", "Levaduras"),
    AnalyteSpec("SED_MOCO", "Filamentos de moco"),
    AnalyteSpec("SED_CRISTALES", "Cristales"),
    AnalyteSpec("SED_CILINDROS_HIALINOS", "Cilindros hialinos", "/[LPF]"),
    AnalyteSpec("SED_OTROS_CILINDROS", "Otros cilindros"),
    AnalyteSpec("ORI_OBSERVACIONES", "Observaciones del uroanálisis"),
    AnalyteSpec("ORI_VOL_24H", "Volumen urinario de 24 horas", "mL/(24.h)"),
    AnalyteSpec("ORI_PROT_DL", "Proteínas en orina (cuantitativo)", "mg/dL"),
    AnalyteSpec(
        "ORI_PROT_24H",
        "Proteinuria de 24 horas",
        "mg/(24.h)",
        description="Calculada: proteínas (mg/dL) x volumen (mL) / 100.",
    ),
)

_NEGATIVO_CRUCES = RangeSpec(option="negativo", text="Negativo")
_ESCASAS = RangeSpec(text="Ausentes o escasas")


def _dipstick(analyte: str, *, expected: RangeSpec = _NEGATIVO_CRUCES):
    return opt(analyte, "cruces", expected, result_type="semi_quantitative")


UROANALISIS = TemplateSpec(
    "UROANALISIS",
    "Uroanálisis completo",
    "Examen físico, químico por tira reactiva y sedimento urinario.",
    (
        SectionSpec(
            "Examen físico",
            (
                opt(
                    "ORI_COLOR",
                    "color_orina",
                    RangeSpec(text="Amarillo claro a amarillo"),
                ),
                opt(
                    "ORI_ASPECTO",
                    "aspecto_orina",
                    RangeSpec(option="transparente", text="Transparente"),
                ),
                num("ORI_DENSIDAD", "{ratio}", 3, between(1.005, 1.030)),
                num("ORI_PH", "[pH]", 1, between(5.0, 8.0)),
            ),
        ),
        SectionSpec(
            "Examen químico",
            (
                _dipstick("ORI_PROTEINAS"),
                _dipstick("ORI_GLUCOSA"),
                _dipstick("ORI_CETONAS"),
                _dipstick("ORI_SANGRE"),
                _dipstick("ORI_BILIRRUBINA"),
                _dipstick(
                    "ORI_UROBILINOGENO",
                    expected=RangeSpec(text="Normal (hasta 1 mg/dL)"),
                ),
                opt(
                    "ORI_NITRITOS",
                    "positividad",
                    RangeSpec(option="negativo", text="Negativo"),
                ),
                _dipstick("ORI_LEUCOCITOS_ESTERASA"),
            ),
        ),
        SectionSpec(
            "Sedimento urinario",
            (
                num("SED_LEUCOCITOS", "/[HPF]", 0, between(0.0, 5.0)),
                num("SED_ERITROCITOS", "/[HPF]", 0, between(0.0, 3.0)),
                opt(
                    "SED_CEL_EPITELIALES",
                    "escasas_abundantes",
                    _ESCASAS,
                    result_type="semi_quantitative",
                ),
                opt(
                    "SED_BACTERIAS",
                    "escasas_abundantes",
                    RangeSpec(option="ausentes", text="Ausentes"),
                    result_type="semi_quantitative",
                ),
                opt(
                    "SED_LEVADURAS",
                    "escasas_abundantes",
                    RangeSpec(option="ausentes", text="Ausentes"),
                    result_type="semi_quantitative",
                ),
                opt(
                    "SED_MOCO",
                    "escasas_abundantes",
                    _ESCASAS,
                    result_type="semi_quantitative",
                ),
                num("SED_CILINDROS_HIALINOS", "/[LPF]", 0, between(0.0, 2.0)),
                text("SED_OTROS_CILINDROS", default="No se observan"),
                text("SED_CRISTALES", default="No se observan"),
            ),
        ),
        SectionSpec("Observaciones", (text("ORI_OBSERVACIONES"),)),
    ),
)

PROTEINURIA_24H = TemplateSpec(
    "PROTEINURIA_24H",
    "Proteinuria en orina de 24 horas",
    "Proteínas en una muestra de la orina de 24 horas, volumen total y "
    "excreción diaria calculada.",
    (
        SectionSpec(
            "Orina de 24 horas",
            (
                num("ORI_VOL_24H", "mL/(24.h)", 0, between(800.0, 2000.0)),
                num("ORI_PROT_DL", "mg/dL", 1, below(15.0, "< 15 mg/dL")),
                calc(
                    "ORI_PROT_24H",
                    "mg/(24.h)",
                    0,
                    "ORI_PROT_DL * ORI_VOL_24H / 100",
                    below(150.0, "< 150 mg/24 h"),
                ),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (UROANALISIS, PROTEINURIA_24H)
