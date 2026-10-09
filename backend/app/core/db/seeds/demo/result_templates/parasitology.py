"""Parasitologia y coprologia: coprologico y coproscopico seriado.

El coprologico combina examen macroscopico, sangre oculta y examen
microscopico directo; el coproscopico seriado informa la busqueda de
parasitos en tres muestras recolectadas en dias diferentes. Reglas de
reporte de uso comun en laboratorios clinicos colombianos; el laboratorio
debe validar los textos por defecto y los valores de referencia.
"""

from app.core.db.seeds.demo.specs import (
    AnalyteSpec,
    RangeSpec,
    SectionSpec,
    TemplateSpec,
    between,
    num,
    opt,
    text,
)

ANALYTES: tuple[AnalyteSpec, ...] = (
    AnalyteSpec("COP_COLOR", "Color de las heces"),
    AnalyteSpec("COP_CONSISTENCIA", "Consistencia de las heces"),
    AnalyteSpec("COP_MOCO", "Moco macroscópico"),
    AnalyteSpec("COP_SANGRE_MACRO", "Sangre macroscópica"),
    AnalyteSpec("COP_SANGRE_OCULTA", "Sangre oculta en heces"),
    AnalyteSpec("COP_LEUCOCITOS", "Leucocitos fecales", "/[HPF]"),
    AnalyteSpec("COP_ERITROCITOS", "Eritrocitos fecales"),
    AnalyteSpec("COP_ALMIDONES", "Gránulos de almidón"),
    AnalyteSpec("COP_GRASAS", "Grasas (gotas de grasa neutra)"),
    AnalyteSpec("COP_FIBRAS", "Fibras musculares"),
    AnalyteSpec("COP_PARASITOS", "Parásitos (examen directo)"),
    AnalyteSpec("COP_OBSERVACIONES", "Observaciones del coprológico"),
    AnalyteSpec("COP_SER_M1", "Coproscópico seriado, muestra 1"),
    AnalyteSpec("COP_SER_M2", "Coproscópico seriado, muestra 2"),
    AnalyteSpec("COP_SER_M3", "Coproscópico seriado, muestra 3"),
    AnalyteSpec("COP_SER_CONCLUSION", "Coproscópico seriado, conclusión"),
)

_AUSENTE = RangeSpec(option="ausente", text="Ausente")
_ESCASAS = RangeSpec(text="Ausentes o escasas")


def _semi(analyte: str):
    return opt(analyte, "escasas_abundantes", _ESCASAS, result_type="semi_quantitative")


COPROLOGICO = TemplateSpec(
    "COPROLOGICO",
    "Coprológico",
    "Examen macroscópico, sangre oculta y examen microscópico directo de heces.",
    (
        SectionSpec(
            "Examen macroscópico",
            (
                text("COP_COLOR", required=True, default="Marrón"),
                opt(
                    "COP_CONSISTENCIA",
                    "consistencia_heces",
                    RangeSpec(option="formada", text="Formada"),
                ),
                opt("COP_MOCO", "presencia", _AUSENTE),
                opt("COP_SANGRE_MACRO", "presencia", _AUSENTE),
            ),
        ),
        SectionSpec(
            "Examen químico",
            (
                opt(
                    "COP_SANGRE_OCULTA",
                    "positividad",
                    RangeSpec(option="negativo", text="Negativo"),
                ),
            ),
        ),
        SectionSpec(
            "Examen microscópico",
            (
                num("COP_LEUCOCITOS", "/[HPF]", 0, between(0.0, 5.0)),
                opt("COP_ERITROCITOS", "presencia", _AUSENTE),
                _semi("COP_ALMIDONES"),
                _semi("COP_GRASAS"),
                _semi("COP_FIBRAS"),
                text(
                    "COP_PARASITOS",
                    required=True,
                    default="No se observan huevos, quistes ni trofozoítos de parásitos",
                ),
            ),
        ),
        SectionSpec("Observaciones", (text("COP_OBSERVACIONES"),)),
    ),
)

COPROSCOPICO_SERIADO = TemplateSpec(
    "COPROSCOPICO_SERIADO",
    "Coproscópico seriado (parásitos)",
    "Búsqueda de parásitos intestinales en tres muestras de días diferentes, "
    "con concentración y examen directo.",
    (
        SectionSpec(
            "Muestras",
            (
                text(
                    "COP_SER_M1",
                    required=True,
                    default="No se observan huevos, quistes ni larvas de parásitos",
                ),
                text(
                    "COP_SER_M2",
                    required=True,
                    default="No se observan huevos, quistes ni larvas de parásitos",
                ),
                text(
                    "COP_SER_M3",
                    required=True,
                    default="No se observan huevos, quistes ni larvas de parásitos",
                ),
            ),
        ),
        SectionSpec("Conclusión", (text("COP_SER_CONCLUSION", required=True),)),
    ),
)

TEMPLATES: tuple[TemplateSpec, ...] = (COPROLOGICO, COPROSCOPICO_SERIADO)
