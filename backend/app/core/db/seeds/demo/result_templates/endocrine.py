"""Endocrinologia y hormonas: tiroides, PSA, cortisol y beta-hCG.

Valores de referencia de ADULTOS por inmunoensayo (Mayo Clinic Laboratories
e insertos de fabricante; TSH en embarazo segun ATA 2011; beta-hCG por
semanas de gestacion segun tablas de uso comun). Los rangos dependen del
metodo y del equipo: el laboratorio debe sustituirlos por los de su plataforma.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    SectionSpec,
    TemplateSpec,
    below,
    between,
    num,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec(
        "TSH", "Hormona estimulante de la tiroides (TSH)", "u[IU]/mL", "3016-3"
    ),
    AnalyteSpec("T4L", "Tiroxina libre (T4 libre)", "ng/dL", "3024-7"),
    AnalyteSpec("T3", "Triyodotironina total (T3 total)", "ng/dL", "3053-6"),
    AnalyteSpec("PSA", "Antígeno prostático específico total (PSA)", "ng/mL", "2857-1"),
    AnalyteSpec("CORTISOL", "Cortisol", "ug/dL", "2143-6"),
    AnalyteSpec(
        "BHCG",
        "Gonadotropina coriónica humana beta (beta-hCG cuantitativa)",
        "m[IU]/mL",
        "21198-7",
    ),
)

TSH = TemplateSpec(
    "TSH",
    "TSH",
    "Hormona estimulante de la tiroides, con rangos para embarazo por trimestre.",
    (
        SectionSpec(
            "Tiroides",
            (
                num(
                    "TSH",
                    "u[IU]/mL",
                    2,
                    between(0.4, 4.0),
                    between(
                        0.1,
                        2.5,
                        sex="female",
                        condition="Embarazo, primer trimestre",
                    ),
                    between(
                        0.2,
                        3.0,
                        sex="female",
                        condition="Embarazo, segundo trimestre",
                    ),
                    between(
                        0.3,
                        3.0,
                        sex="female",
                        condition="Embarazo, tercer trimestre",
                    ),
                ),
            ),
        ),
    ),
)

T4_LIBRE = TemplateSpec(
    "T4_LIBRE",
    "T4 libre",
    "Tiroxina libre.",
    (SectionSpec("Tiroides", (num("T4L", "ng/dL", 2, between(0.9, 1.7)),)),),
)

T3_TOTAL = TemplateSpec(
    "T3_TOTAL",
    "T3 total",
    "Triyodotironina total.",
    (SectionSpec("Tiroides", (num("T3", "ng/dL", 0, between(80.0, 200.0)),)),),
)

PSA_TOTAL = TemplateSpec(
    "PSA_TOTAL",
    "PSA total",
    "Antígeno prostático específico total en hombres.",
    (
        SectionSpec(
            "Marcador tumoral",
            (
                num(
                    "PSA",
                    "ng/mL",
                    2,
                    below(
                        4.0,
                        "< 4,0 ng/mL",
                        sex="male",
                        interpretation="Un valor elevado no confirma cáncer: debe "
                        "interpretarse con la edad, el tacto rectal y la clínica.",
                    ),
                ),
            ),
        ),
    ),
)

CORTISOL_AM = TemplateSpec(
    "CORTISOL",
    "Cortisol sérico",
    "Cortisol en suero; el rango depende de la hora de la toma.",
    (
        SectionSpec(
            "Función suprarrenal",
            (
                num(
                    "CORTISOL",
                    "ug/dL",
                    1,
                    between(
                        6.2,
                        19.4,
                        condition="Muestra de la mañana (7:00 - 9:00 a. m.)",
                    ),
                    between(
                        2.3,
                        11.9,
                        condition="Muestra de la tarde (4:00 - 8:00 p. m.)",
                    ),
                ),
            ),
        ),
    ),
)

BHCG = TemplateSpec(
    "BHCG",
    "Beta-hCG cuantitativa",
    "Gonadotropina coriónica beta en suero, con rangos por semanas de "
    "gestación (desde la fecha de la última menstruación).",
    (
        SectionSpec(
            "Embarazo",
            (
                num(
                    "BHCG",
                    "m[IU]/mL",
                    1,
                    below(5.0, "< 5 mUI/mL", condition="No gestante"),
                    between(5.0, 50.0, sex="female", condition="Gestación, 3 semanas"),
                    between(5.0, 426.0, sex="female", condition="Gestación, 4 semanas"),
                    between(
                        18.0, 7340.0, sex="female", condition="Gestación, 5 semanas"
                    ),
                    between(
                        1080.0, 56500.0, sex="female", condition="Gestación, 6 semanas"
                    ),
                    between(
                        7650.0,
                        229000.0,
                        sex="female",
                        condition="Gestación, 7 a 8 semanas",
                    ),
                    between(
                        25700.0,
                        288000.0,
                        sex="female",
                        condition="Gestación, 9 a 12 semanas",
                    ),
                ),
            ),
        ),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (
    TSH,
    T4_LIBRE,
    T3_TOTAL,
    PSA_TOTAL,
    CORTISOL_AM,
    BHCG,
)
