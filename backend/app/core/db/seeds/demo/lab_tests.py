"""Examenes de laboratorio de la demostracion.

Cada examen referencia por `code` su area, tipos de muestra (>= 1 y uno
preferido), precondiciones (con overrides donde aplica), etiqueta, plantilla
de resultados y documentos a firmar; `load` resuelve esos codigos con los ids
ya creados y usa la API (`POST /lab-tests` + `PUT` de precondiciones y
documentos). Los `cups_code` y `loinc_code` del examen se dejan vacios: el
laboratorio debe completarlos con su tarifario (CUPS) y verificarlos.

Volumenes (`required_volume_ml`) = volumen del TUBO o recipiente de toma.
"""

from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class SampleLink(NamedTuple):
    sample_type: str
    preferred: bool = False
    volume_ml: float | None = None


class PreconditionLink(NamedTuple):
    precondition: str
    mandatory: bool = True
    name_override: str | None = None
    description_override: str | None = None
    duration_value_override: float | None = None
    duration_unit_override: str | None = None
    instructions_override: str | None = None


class LabTestSeed(NamedTuple):
    code: str
    name: str
    abbreviation: str
    description: str
    area: str
    method: str
    turnaround_hours: int
    template: str  # code de la plantilla (version 1 publicada)
    label: str  # code de la etiqueta (version 1 publicada)
    samples: tuple[SampleLink, ...]
    preconditions: tuple[PreconditionLink, ...] = ()
    consents: tuple[str, ...] = ()  # documentos propios del examen (solo VIH)


def _serum(volume: float = 3.0) -> tuple[SampleLink, ...]:
    """Suero: dorado preferido, rojo alterno."""
    return (
        SampleLink("TUBO_DORADO", True, volume),
        SampleLink("TUBO_ROJO", False, volume),
    )


_AYUNO_8H = PreconditionLink("AYUNO_8H")
_AYUNO_8H_OPCIONAL = PreconditionLink("AYUNO_8H", mandatory=False)
_BIOTINA = PreconditionLink("SIN_BIOTINA")
_EJERCICIO_OPCIONAL = PreconditionLink("SIN_EJERCICIO", mandatory=False)

LAB_TESTS: tuple[LabTestSeed, ...] = (
    LabTestSeed(
        "HEMOGRAMA",
        "Hemograma completo",
        "HEMO",
        "Recuento y morfología básica de eritrocitos, leucocitos con "
        "diferencial y plaquetas, con índices eritrocitarios.",
        "HEM",
        "Citometría de flujo e impedancia (analizador hematológico automatizado)",
        4,
        "HEMOGRAMA",
        "ETQ_TUBO",
        (SampleLink("TUBO_LILA", True, 3.0),),
    ),
    LabTestSeed(
        "GLUCOSA",
        "Glucosa en ayunas",
        "GLU",
        "Glucosa en suero o plasma en ayunas.",
        "QUI",
        "Enzimático (hexocinasa)",
        4,
        "GLUCOSA",
        "ETQ_TUBO",
        (
            SampleLink("TUBO_GRIS", True, 2.0),
            SampleLink("TUBO_DORADO", False, 3.0),
        ),
        (_AYUNO_8H,),
    ),
    LabTestSeed(
        "PERFIL_LIPIDICO",
        "Perfil lipídico",
        "LIPIDOS",
        "Colesterol total, HDL, LDL, VLDL, triglicéridos e índice aterogénico.",
        "QUI",
        "Enzimático colorimétrico",
        24,
        "PERFIL_LIPIDICO",
        "ETQ_TUBO",
        _serum(5.0),
        (PreconditionLink("AYUNO_12H"), _EJERCICIO_OPCIONAL),
    ),
    LabTestSeed(
        "PERFIL_HEPATICO",
        "Perfil hepático",
        "HEPATICO",
        "AST, ALT, fosfatasa alcalina, GGT, bilirrubinas y proteínas.",
        "QUI",
        "Fotometría cinética (IFCC) y colorimétrico",
        24,
        "PERFIL_HEPATICO",
        "ETQ_TUBO",
        _serum(5.0),
        (
            PreconditionLink(
                "AYUNO_8H",
                mandatory=False,
                description_override="Se recomienda el ayuno de 8 horas; no es "
                "obligatorio para las enzimas hepáticas, pero evita suero lipémico.",
            ),
        ),
    ),
    LabTestSeed(
        "CREATININA",
        "Creatinina",
        "CREA",
        "Creatinina sérica, marcador de función renal.",
        "QUI",
        "Jaffé cinético compensado",
        8,
        "CREATININA",
        "ETQ_TUBO",
        _serum(),
        (_AYUNO_8H_OPCIONAL, _EJERCICIO_OPCIONAL),
    ),
    LabTestSeed(
        "UREA_BUN",
        "Urea y nitrógeno ureico (BUN)",
        "UREA",
        "Urea sérica y BUN calculado.",
        "QUI",
        "Ureasa-GLDH cinético UV",
        8,
        "UREA_BUN",
        "ETQ_TUBO",
        _serum(),
        (_AYUNO_8H_OPCIONAL,),
    ),
    LabTestSeed(
        "ACIDO_URICO",
        "Ácido úrico",
        "URICO",
        "Ácido úrico sérico.",
        "QUI",
        "Enzimático (uricasa)",
        8,
        "ACIDO_URICO",
        "ETQ_TUBO",
        _serum(),
        (_AYUNO_8H,),
    ),
    LabTestSeed(
        "ELECTROLITOS",
        "Electrolitos séricos (Na, K, Cl)",
        "ELECTRO",
        "Sodio, potasio y cloro.",
        "QUI",
        "Electrodo ion selectivo indirecto",
        8,
        "ELECTROLITOS",
        "ETQ_TUBO",
        (
            SampleLink("TUBO_DORADO", True, 3.0),
            SampleLink("TUBO_VERDE", False, 4.0),
        ),
    ),
    LabTestSeed(
        "CALCIO",
        "Calcio total",
        "CA",
        "Calcio total sérico.",
        "QUI",
        "Colorimétrico (arsenazo III)",
        8,
        "CALCIO",
        "ETQ_TUBO",
        (
            SampleLink("TUBO_DORADO", True, 3.0),
            SampleLink("TUBO_VERDE", False, 4.0),
        ),
        (_AYUNO_8H_OPCIONAL,),
    ),
    LabTestSeed(
        "HBA1C",
        "Hemoglobina glicosilada (HbA1c)",
        "HBA1C",
        "Control glucémico de los últimos 2 a 3 meses. No requiere ayuno.",
        "QUI",
        "Inmunoensayo turbidimétrico (sangre total con EDTA)",
        24,
        "HBA1C",
        "ETQ_TUBO",
        (SampleLink("TUBO_LILA", True, 3.0),),
    ),
    LabTestSeed(
        "TSH",
        "Hormona estimulante de la tiroides (TSH)",
        "TSH",
        "Tamización y seguimiento de la función tiroidea.",
        "END",
        "Quimioluminiscencia (CLIA)",
        24,
        "TSH",
        "ETQ_TUBO",
        _serum(),
        (
            PreconditionLink(
                "SIN_BIOTINA",
                duration_value_override=48,
                duration_unit_override="horas",
                instructions_override="Suspenda los suplementos con biotina 48 "
                "horas antes de la toma (72 horas si toma dosis altas formuladas).",
            ),
        ),
    ),
    LabTestSeed(
        "T4_LIBRE",
        "T4 libre",
        "T4L",
        "Tiroxina libre.",
        "END",
        "Quimioluminiscencia (CLIA)",
        24,
        "T4_LIBRE",
        "ETQ_TUBO",
        _serum(),
        (_BIOTINA,),
    ),
    LabTestSeed(
        "T3_TOTAL",
        "T3 total",
        "T3",
        "Triyodotironina total.",
        "END",
        "Quimioluminiscencia (CLIA)",
        24,
        "T3_TOTAL",
        "ETQ_TUBO",
        _serum(),
        (_BIOTINA,),
    ),
    LabTestSeed(
        "PSA_TOTAL",
        "Antígeno prostático específico total (PSA)",
        "PSA",
        "PSA total en hombres: seguimiento y detección temprana de enfermedad prostática.",
        "END",
        "Quimioluminiscencia (CLIA)",
        24,
        "PSA_TOTAL",
        "ETQ_TUBO",
        _serum(),
        (PreconditionLink("PREPARACION_PSA"), _BIOTINA),
    ),
    LabTestSeed(
        "CORTISOL",
        "Cortisol sérico",
        "CORT",
        "Cortisol en suero (muestra de la mañana).",
        "END",
        "Quimioluminiscencia (CLIA)",
        48,
        "CORTISOL",
        "ETQ_TUBO",
        _serum(),
        (
            PreconditionLink("CORTISOL_MANANA"),
            PreconditionLink("SIN_EJERCICIO"),
            _BIOTINA,
        ),
    ),
    LabTestSeed(
        "BHCG",
        "Beta-hCG cuantitativa",
        "BHCG",
        "Gonadotropina coriónica humana beta cuantitativa en suero.",
        "END",
        "Quimioluminiscencia (CLIA)",
        12,
        "BHCG",
        "ETQ_TUBO",
        _serum(),
        (_BIOTINA,),
    ),
    LabTestSeed(
        "VIH",
        "VIH 1/2 antígeno/anticuerpo",
        "VIH",
        "Tamización de VIH de 4.ª generación. Requiere consentimiento y asesoría.",
        "INM",
        "Inmunoensayo de quimioluminiscencia (4.ª generación)",
        24,
        "VIH",
        "ETQ_ALICUOTA",
        _serum(),
        (),
        ("CONSENT_VIH",),
    ),
    LabTestSeed(
        "VDRL",
        "VDRL / RPR",
        "VDRL",
        "Prueba no treponémica para sífilis, con titulación si es reactiva.",
        "INM",
        "Floculación (VDRL/RPR) con titulación",
        24,
        "VDRL",
        "ETQ_ALICUOTA",
        _serum(),
    ),
    LabTestSeed(
        "HBSAG",
        "Antígeno de superficie de hepatitis B (HBsAg)",
        "HBSAG",
        "Tamización de hepatitis B.",
        "INM",
        "Inmunoensayo de quimioluminiscencia",
        24,
        "HBSAG",
        "ETQ_ALICUOTA",
        _serum(),
    ),
    LabTestSeed(
        "ANTI_HCV",
        "Anticuerpos anti-hepatitis C (anti-HCV)",
        "ANTIHCV",
        "Tamización de hepatitis C.",
        "INM",
        "Inmunoensayo de quimioluminiscencia",
        24,
        "ANTI_HCV",
        "ETQ_ALICUOTA",
        _serum(),
    ),
    LabTestSeed(
        "PCR",
        "Proteína C reactiva cuantitativa",
        "PCR",
        "Marcador de inflamación aguda.",
        "INM",
        "Inmunoturbidimetría",
        12,
        "PCR",
        "ETQ_TUBO",
        _serum(),
    ),
    LabTestSeed(
        "FACTOR_REUMATOIDE",
        "Factor reumatoide",
        "FR",
        "Factor reumatoide cuantitativo.",
        "INM",
        "Inmunoturbidimetría",
        24,
        "FACTOR_REUMATOIDE",
        "ETQ_TUBO",
        _serum(),
    ),
    LabTestSeed(
        "GRUPO_RH",
        "Grupo sanguíneo y Rh",
        "GRUPORH",
        "Grupo ABO y factor Rh (D).",
        "INM",
        "Aglutinación en gel (prueba directa e inversa)",
        6,
        "GRUPO_RH",
        "ETQ_TUBO",
        (SampleLink("TUBO_LILA", True, 3.0),),
    ),
    LabTestSeed(
        "EMBARAZO_ORINA",
        "Prueba de embarazo en orina",
        "HCGORINA",
        "Detección cualitativa de hCG en orina.",
        "INM",
        "Inmunocromatografía",
        2,
        "EMBARAZO_ORINA",
        "ETQ_FRASCO",
        (SampleLink("ORINA_FRASCO", True, 10.0),),
        (
            PreconditionLink(
                "PRIMERA_ORINA",
                mandatory=False,
                name_override="Primera orina de la mañana (recomendada)",
            ),
        ),
    ),
    LabTestSeed(
        "UROANALISIS",
        "Uroanálisis completo",
        "UROANAL",
        "Examen físico, químico y microscópico del sedimento urinario.",
        "URO",
        "Tira reactiva y microscopía del sedimento",
        4,
        "UROANALISIS",
        "ETQ_FRASCO",
        (SampleLink("ORINA_FRASCO", True, 10.0),),
        (PreconditionLink("PRIMERA_ORINA", mandatory=False),),
    ),
    LabTestSeed(
        "PROTEINURIA_24H",
        "Proteinuria en orina de 24 horas",
        "PROT24H",
        "Excreción diaria de proteínas en orina.",
        "URO",
        "Colorimétrico (rojo de pirogalol)",
        48,
        "PROTEINURIA_24H",
        "ETQ_FRASCO",
        (SampleLink("ORINA_24H", True, None),),
        (PreconditionLink("ORINA_24H"), _EJERCICIO_OPCIONAL),
    ),
    LabTestSeed(
        "TP_INR",
        "Tiempo de protrombina e INR",
        "TP",
        "TP, relación e INR; control de la terapia con warfarina.",
        "COA",
        "Coagulométrico (nefelometría óptica)",
        4,
        "TP_INR",
        "ETQ_TUBO",
        (SampleLink("TUBO_AZUL", True, 2.7),),
    ),
    LabTestSeed(
        "TTP",
        "Tiempo parcial de tromboplastina (TTP)",
        "TTP",
        "TTP activado; control de la terapia con heparina.",
        "COA",
        "Coagulométrico (nefelometría óptica)",
        4,
        "TTP",
        "ETQ_TUBO",
        (SampleLink("TUBO_AZUL", True, 2.7),),
    ),
    LabTestSeed(
        "FIBRINOGENO",
        "Fibrinógeno",
        "FIBR",
        "Fibrinógeno funcional.",
        "COA",
        "Método de Clauss",
        6,
        "FIBRINOGENO",
        "ETQ_TUBO",
        (SampleLink("TUBO_AZUL", True, 2.7),),
    ),
    LabTestSeed(
        "COPROLOGICO",
        "Coprológico",
        "COPRO",
        "Examen macroscópico, sangre oculta y microscópico directo de heces.",
        "PAR",
        "Examen macroscópico y microscópico directo",
        24,
        "COPROLOGICO",
        "ETQ_FRASCO",
        (SampleLink("HECES_RECOLECTOR", True, None),),
        (PreconditionLink("RECOLECCION_HECES"),),
    ),
    LabTestSeed(
        "COPROSCOPICO_SERIADO",
        "Coproscópico seriado (parásitos)",
        "COPROSER",
        "Búsqueda de parásitos intestinales en tres muestras seriadas.",
        "PAR",
        "Concentración (formol-éter) y examen directo",
        48,
        "COPROSCOPICO_SERIADO",
        "ETQ_FRASCO",
        (SampleLink("HECES_SERIADO", True, None),),
        (PreconditionLink("RECOLECCION_HECES"),),
    ),
    LabTestSeed(
        "UROCULTIVO",
        "Urocultivo con antibiograma",
        "UROCULT",
        "Cultivo cuantitativo de orina con identificación y antibiograma.",
        "MIC",
        "Cultivo en agar sangre y MacConkey; antibiograma por difusión en disco",
        72,
        "UROCULTIVO",
        "ETQ_ORDEN",
        (SampleLink("ORINA_CULTIVO", True, 10.0),),
        (
            PreconditionLink("PRIMERA_ORINA"),
            PreconditionLink("ANTIBIOTICOS", mandatory=False),
        ),
    ),
    LabTestSeed(
        "COPROCULTIVO",
        "Coprocultivo con antibiograma",
        "COPROC",
        "Cultivo de heces para patógenos entéricos con antibiograma.",
        "MIC",
        "Cultivo en medios selectivos y diferenciales; antibiograma por difusión en disco",
        96,
        "COPROCULTIVO",
        "ETQ_ORDEN",
        (
            SampleLink("HECES_CULTIVO", True, None),
            SampleLink("HECES_RECOLECTOR", False, None),
        ),
        (
            PreconditionLink("RECOLECCION_HECES"),
            PreconditionLink("ANTIBIOTICOS", mandatory=False),
        ),
    ),
)


def consent_codes(test: LabTestSeed) -> list[str]:
    """Documentos propios del examen. Solo VIH exige uno; el consentimiento
    general de datos personales no se enlaza a examenes (la app de firmas lo
    pide primero a todo paciente)."""
    return list(test.consents)


async def load(api: DemoApi, registry: Registry) -> None:
    for test in LAB_TESTS:
        created = await api.post(
            "/lab-tests",
            {
                "code": test.code,
                "name": test.name,
                "abbreviation": test.abbreviation,
                "description": test.description,
                "area_id": registry.areas[test.area],
                "method": test.method,
                "turnaround_hours": test.turnaround_hours,
                "print_label_version_id": registry.label_versions[test.label],
                "result_template_version_id": registry.template_versions[test.template],
                "sample_types": [
                    {
                        "sample_type_id": registry.sample_types[link.sample_type],
                        "is_preferred": link.preferred,
                        "required_volume_ml": link.volume_ml,
                        "sort_order": order,
                    }
                    for order, link in enumerate(test.samples, start=1)
                ],
            },
        )
        registry.lab_tests[test.code] = created["id"]
        base = f"/lab-tests/{created['id']}"
        if test.preconditions:
            await api.put(
                f"{base}/preconditions",
                [
                    {
                        "precondition_id": registry.preconditions[link.precondition],
                        "is_mandatory": link.mandatory,
                        "sort_order": order,
                        "name_override": link.name_override,
                        "description_override": link.description_override,
                        "duration_value_override": link.duration_value_override,
                        "duration_unit_override": link.duration_unit_override,
                        "patient_instructions_override": link.instructions_override,
                    }
                    for order, link in enumerate(test.preconditions, start=1)
                ],
            )
        if consent_codes(test):
            await api.put(
                f"{base}/consent-documents",
                [
                    {
                        "consent_document_version_id": registry.consent_versions[code],
                        "is_mandatory": True,
                    }
                    for code in consent_codes(test)
                ],
            )
