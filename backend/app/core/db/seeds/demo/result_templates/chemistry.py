"""Quimica clinica: glucosa, perfil lipidico, perfil hepatico, funcion renal,
electrolitos, calcio y hemoglobina glicosilada.

Valores de referencia de ADULTOS en suero/plasma, tomados de fuentes de uso
comun (Mayo Clinic Laboratories, ATP III / ADA para glucosa, lipidos y
HbA1c); rangos por sexo donde la fuente los distingue. Las formulas
(Friedewald para LDL y VLDL, BUN = urea x 0,467, glucosa promedio estimada
ADAG = 28,7 x HbA1c - 46,7) son las estandar. A validar con el laboratorio
segun su metodo y su poblacion.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    SectionSpec,
    TemplateSpec,
    above,
    below,
    between,
    calc,
    num,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec("GLU", "Glucosa", "mg/dL", "2345-7"),
    AnalyteSpec("COL_TOTAL", "Colesterol total", "mg/dL", "2093-3"),
    AnalyteSpec("HDL", "Colesterol HDL", "mg/dL", "2085-9"),
    AnalyteSpec(
        "LDL",
        "Colesterol LDL (calculado)",
        "mg/dL",
        "13457-7",
        "Fórmula de Friedewald: CT - HDL - TG/5. No válida si los triglicéridos "
        "superan 400 mg/dL (solicitar LDL directo).",
    ),
    AnalyteSpec(
        "VLDL",
        "Colesterol VLDL (calculado)",
        "mg/dL",
        "13458-5",
        "Estimado como triglicéridos / 5.",
    ),
    AnalyteSpec("TG", "Triglicéridos", "mg/dL", "2571-8"),
    AnalyteSpec(
        "IND_ATEROGENICO",
        "Índice aterogénico (CT/HDL)",
        "{ratio}",
        None,
        "Relación colesterol total / colesterol HDL.",
    ),
    AnalyteSpec("CREA", "Creatinina", "mg/dL", "2160-0"),
    AnalyteSpec("UREA", "Urea", "mg/dL"),
    AnalyteSpec(
        "BUN",
        "Nitrógeno ureico (BUN)",
        "mg/dL",
        "3094-0",
        "Calculado: urea x 0,467.",
    ),
    AnalyteSpec("AC_URICO", "Ácido úrico", "mg/dL", "3084-1"),
    AnalyteSpec("AST", "Aspartato aminotransferasa (AST/TGO)", "U/L", "1920-8"),
    AnalyteSpec("ALT", "Alanina aminotransferasa (ALT/TGP)", "U/L", "1742-6"),
    AnalyteSpec("FA", "Fosfatasa alcalina", "U/L", "6768-6"),
    AnalyteSpec("GGT", "Gamma glutamil transferasa (GGT)", "U/L", "2324-2"),
    AnalyteSpec("BIL_TOTAL", "Bilirrubina total", "mg/dL", "1975-2"),
    AnalyteSpec("BIL_DIRECTA", "Bilirrubina directa", "mg/dL", "1968-7"),
    AnalyteSpec(
        "BIL_INDIRECTA",
        "Bilirrubina indirecta",
        "mg/dL",
        "1971-1",
        "Calculada: bilirrubina total - bilirrubina directa.",
    ),
    AnalyteSpec("PROT_TOTAL", "Proteínas totales", "g/dL", "2885-2"),
    AnalyteSpec("ALBUMINA", "Albúmina", "g/dL", "1751-7"),
    AnalyteSpec(
        "GLOBULINAS",
        "Globulinas",
        "g/dL",
        "10834-0",
        "Calculadas: proteínas totales - albúmina.",
    ),
    AnalyteSpec(
        "REL_ALB_GLOB",
        "Relación albúmina/globulina",
        "{ratio}",
        "1759-0",
        "Calculada: albúmina / globulinas.",
    ),
    AnalyteSpec("NA", "Sodio", "mmol/L", "2951-2"),
    AnalyteSpec("K", "Potasio", "mmol/L", "2823-3"),
    AnalyteSpec("CL", "Cloro", "mmol/L", "2075-0"),
    AnalyteSpec("CA", "Calcio total", "mg/dL", "17861-6"),
    AnalyteSpec("HBA1C", "Hemoglobina glicosilada (HbA1c)", "%", "4548-4"),
    AnalyteSpec(
        "GLU_PROM_EST",
        "Glucosa promedio estimada (eAG)",
        "mg/dL",
        None,
        "Calculada desde la HbA1c: 28,7 x HbA1c - 46,7 (estudio ADAG).",
    ),
    AnalyteSpec(
        "CKMB",
        "CK-MB (masa)",
        "ng/mL",
        None,
        "Marcador cardíaco; ya no se procesa en la sede.",
    ),
)

GLUCOSA = TemplateSpec(
    "GLUCOSA",
    "Glucosa en ayunas",
    "Glucosa en suero o plasma en ayunas.",
    (
        SectionSpec(
            "Glucosa",
            (
                num(
                    "GLU",
                    "mg/dL",
                    0,
                    between(
                        70.0,
                        99.0,
                        critical_low=40.0,
                        critical_high=500.0,
                        interpretation="100-125 mg/dL: glucosa alterada en ayunas "
                        "(prediabetes). >= 126 mg/dL en dos ocasiones: compatible "
                        "con diabetes mellitus (criterio ADA).",
                    ),
                ),
            ),
        ),
    ),
)

PERFIL_LIPIDICO = TemplateSpec(
    "PERFIL_LIPIDICO",
    "Perfil lipídico",
    "Colesterol total, HDL, LDL y VLDL calculados, triglicéridos e índice "
    "aterogénico. Requiere ayuno de 12 horas.",
    (
        SectionSpec(
            "Perfil lipídico",
            (
                num(
                    "COL_TOTAL",
                    "mg/dL",
                    0,
                    below(
                        200.0,
                        "< 200 mg/dL (deseable)",
                        interpretation="200-239 mg/dL: límite alto. >= 240 mg/dL: alto.",
                    ),
                ),
                num(
                    "TG",
                    "mg/dL",
                    0,
                    below(
                        150.0,
                        "< 150 mg/dL (normal)",
                        interpretation="150-199 límite alto; 200-499 alto; >= 500 "
                        "muy alto (riesgo de pancreatitis).",
                    ),
                ),
                num(
                    "HDL",
                    "mg/dL",
                    0,
                    above(40.0, "> 40 mg/dL", sex="male"),
                    above(50.0, "> 50 mg/dL", sex="female"),
                ),
                calc(
                    "LDL",
                    "mg/dL",
                    0,
                    "COL_TOTAL - HDL - TG / 5",
                    below(
                        100.0,
                        "< 100 mg/dL (óptimo)",
                        interpretation="100-129 casi óptimo; 130-159 límite alto; "
                        "160-189 alto; >= 190 muy alto.",
                    ),
                ),
                calc("VLDL", "mg/dL", 0, "TG / 5", between(5.0, 30.0)),
                calc(
                    "IND_ATEROGENICO",
                    "{ratio}",
                    1,
                    "COL_TOTAL / HDL",
                    below(5.0, "< 5,0"),
                ),
            ),
        ),
    ),
)

PERFIL_HEPATICO = TemplateSpec(
    "PERFIL_HEPATICO",
    "Perfil hepático",
    "Transaminasas, fosfatasa alcalina, GGT, bilirrubinas y proteínas.",
    (
        SectionSpec(
            "Enzimas hepáticas",
            (
                num(
                    "AST",
                    "U/L",
                    0,
                    between(8.0, 48.0, sex="male"),
                    between(8.0, 43.0, sex="female"),
                ),
                num(
                    "ALT",
                    "U/L",
                    0,
                    between(7.0, 55.0, sex="male"),
                    between(7.0, 45.0, sex="female"),
                ),
                num(
                    "FA",
                    "U/L",
                    0,
                    between(40.0, 129.0, sex="male"),
                    between(35.0, 104.0, sex="female"),
                ),
                num(
                    "GGT",
                    "U/L",
                    0,
                    between(8.0, 61.0, sex="male"),
                    between(5.0, 36.0, sex="female"),
                ),
            ),
        ),
        SectionSpec(
            "Bilirrubinas",
            (
                num("BIL_TOTAL", "mg/dL", 2, between(0.1, 1.2)),
                num("BIL_DIRECTA", "mg/dL", 2, between(0.0, 0.3)),
                calc(
                    "BIL_INDIRECTA",
                    "mg/dL",
                    2,
                    "BIL_TOTAL - BIL_DIRECTA",
                    between(0.1, 1.0),
                ),
            ),
        ),
        SectionSpec(
            "Proteínas",
            (
                num("PROT_TOTAL", "g/dL", 1, between(6.3, 7.9)),
                num("ALBUMINA", "g/dL", 1, between(3.5, 5.0)),
                calc(
                    "GLOBULINAS",
                    "g/dL",
                    1,
                    "PROT_TOTAL - ALBUMINA",
                    between(2.0, 3.5),
                ),
                calc(
                    "REL_ALB_GLOB",
                    "{ratio}",
                    1,
                    "ALBUMINA / GLOBULINAS",
                    between(1.1, 2.5),
                ),
            ),
        ),
    ),
)

CREATININA = TemplateSpec(
    "CREATININA",
    "Creatinina",
    "Creatinina sérica. Rangos de adultos por sexo.",
    (
        SectionSpec(
            "Función renal",
            (
                num(
                    "CREA",
                    "mg/dL",
                    2,
                    between(0.74, 1.35, sex="male", critical_high=10.0),
                    between(0.59, 1.04, sex="female", critical_high=10.0),
                ),
            ),
        ),
    ),
)

UREA_BUN = TemplateSpec(
    "UREA_BUN",
    "Urea y nitrógeno ureico (BUN)",
    "Urea sérica y BUN calculado.",
    (
        SectionSpec(
            "Función renal",
            (
                num("UREA", "mg/dL", 0, between(15.0, 43.0)),
                calc("BUN", "mg/dL", 1, "UREA * 0.467", between(7.0, 20.0)),
            ),
        ),
    ),
)

ACIDO_URICO = TemplateSpec(
    "ACIDO_URICO",
    "Ácido úrico",
    "Ácido úrico sérico. Rangos de adultos por sexo.",
    (
        SectionSpec(
            "Ácido úrico",
            (
                num(
                    "AC_URICO",
                    "mg/dL",
                    1,
                    between(3.4, 7.0, sex="male"),
                    between(2.4, 6.0, sex="female"),
                ),
            ),
        ),
    ),
)

ELECTROLITOS = TemplateSpec(
    "ELECTROLITOS",
    "Electrolitos séricos (Na, K, Cl)",
    "Sodio, potasio y cloro por electrodo ion selectivo.",
    (
        SectionSpec(
            "Electrolitos",
            (
                num(
                    "NA",
                    "mmol/L",
                    0,
                    between(135.0, 145.0, critical_low=120.0, critical_high=160.0),
                ),
                num(
                    "K",
                    "mmol/L",
                    1,
                    between(3.5, 5.1, critical_low=2.5, critical_high=6.5),
                ),
                num("CL", "mmol/L", 0, between(98.0, 107.0)),
            ),
        ),
    ),
)

CALCIO = TemplateSpec(
    "CALCIO",
    "Calcio total",
    "Calcio total sérico.",
    (
        SectionSpec(
            "Calcio",
            (
                num(
                    "CA",
                    "mg/dL",
                    1,
                    between(8.6, 10.2, critical_low=6.5, critical_high=13.0),
                ),
            ),
        ),
    ),
)

HBA1C = TemplateSpec(
    "HBA1C",
    "Hemoglobina glicosilada (HbA1c)",
    "HbA1c en sangre total con EDTA y glucosa promedio estimada.",
    (
        SectionSpec(
            "Control glucémico",
            (
                num(
                    "HBA1C",
                    "%",
                    1,
                    between(
                        4.0,
                        5.6,
                        interpretation="5,7-6,4 %: prediabetes. >= 6,5 %: compatible "
                        "con diabetes mellitus (criterio ADA). Meta en diabéticos "
                        "adultos: < 7,0 %.",
                    ),
                ),
                calc(
                    "GLU_PROM_EST",
                    "mg/dL",
                    0,
                    "28.7 * HBA1C - 46.7",
                    between(68.0, 114.0),
                ),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (
    GLUCOSA,
    PERFIL_LIPIDICO,
    PERFIL_HEPATICO,
    CREATININA,
    UREA_BUN,
    ACIDO_URICO,
    ELECTROLITOS,
    CALCIO,
    HBA1C,
)
