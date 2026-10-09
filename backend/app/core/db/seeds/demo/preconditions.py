"""Precondiciones del paciente (jerarquia de un nivel: raiz + items).

Indicaciones preanaliticas habituales de laboratorio clinico (ayuno,
suspension de biotina, recoleccion de orina y heces...). Las duraciones son
las recomendaciones tipicas; el laboratorio debe validarlas con su manual de
toma de muestras.
"""

from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class ConditionSeed(NamedTuple):
    code: str
    name: str
    category: str
    instructions: str
    duration_value: float | None = None
    duration_unit: str | None = None


class PreconditionSeed(NamedTuple):
    code: str
    name: str
    description: str
    category: str
    instructions: str
    duration_value: float | None
    duration_unit: str | None
    items: tuple[ConditionSeed, ...]


PRECONDITIONS: tuple[PreconditionSeed, ...] = (
    PreconditionSeed(
        "AYUNO_8H",
        "Ayuno de 8 horas",
        "Ayuno previo a la toma de sangre para glucosa y otros analitos "
        "sensibles a la ingesta de alimentos.",
        "ayuno",
        "No consuma alimentos ni bebidas (excepto agua) durante las 8 horas "
        "previas a la toma de la muestra.",
        8,
        "horas",
        (
            ConditionSeed(
                "AYUNO_8H_AGUA",
                "Solo se permite agua",
                "dieta",
                "Puede tomar agua sola. Evite café, té, jugos, bebidas "
                "azucaradas y chicle.",
            ),
            ConditionSeed(
                "AYUNO_8H_CENA",
                "Cena liviana la noche anterior",
                "dieta",
                "La noche anterior cene liviano, sin comidas muy grasas ni alcohol.",
            ),
            ConditionSeed(
                "AYUNO_8H_MEDICAMENTOS",
                "Medicamentos de uso diario",
                "medicamentos",
                "No suspenda por su cuenta los medicamentos formulados; "
                "consulte a su médico y avise al personal de toma de muestras "
                "cuáles toma.",
            ),
        ),
    ),
    PreconditionSeed(
        "AYUNO_12H",
        "Ayuno de 12 horas",
        "Ayuno estricto previo al perfil lipídico (los triglicéridos aumentan "
        "tras las comidas).",
        "ayuno",
        "No consuma alimentos ni bebidas (excepto agua) durante 12 horas "
        "antes de la toma de la muestra.",
        12,
        "horas",
        (
            ConditionSeed(
                "AYUNO_12H_AGUA",
                "Solo se permite agua",
                "dieta",
                "Puede tomar agua sola. No consuma café, té, jugos ni goma de mascar.",
            ),
            ConditionSeed(
                "AYUNO_12H_ALCOHOL",
                "Sin alcohol previo",
                "alcohol_sustancias",
                "No consuma bebidas alcohólicas en las 24 horas previas: "
                "elevan los triglicéridos.",
                24,
                "horas",
            ),
            ConditionSeed(
                "AYUNO_12H_DIETA",
                "Dieta habitual los días previos",
                "dieta",
                "Mantenga su alimentación habitual en los días previos; no "
                "haga dietas extremas.",
            ),
        ),
    ),
    PreconditionSeed(
        "SIN_EJERCICIO",
        "Sin ejercicio intenso previo",
        "El ejercicio intenso eleva transitoriamente CK, creatinina, AST y "
        "otros analitos, y puede alterar el hemograma.",
        "actividad_fisica",
        "No realice ejercicio físico intenso durante las 24 horas previas a "
        "la toma de la muestra.",
        24,
        "horas",
        (
            ConditionSeed(
                "SIN_EJERCICIO_ENTRENAMIENTO",
                "Sin entrenamiento de fuerza ni resistencia",
                "actividad_fisica",
                "Evite pesas, carreras, ciclismo y deportes de competencia.",
                24,
                "horas",
            ),
            ConditionSeed(
                "SIN_EJERCICIO_REPOSO",
                "Reposo antes de la toma",
                "reposo",
                "Descanse sentado unos 15 minutos antes de la toma de la muestra.",
                15,
                "minutos",
            ),
        ),
    ),
    PreconditionSeed(
        "PRIMERA_ORINA",
        "Primera orina de la mañana",
        "La primera orina del día es la más concentrada y la más adecuada "
        "para uroanálisis, urocultivo y pruebas de embarazo.",
        "recoleccion_muestra",
        "Recoja la primera orina de la mañana, al levantarse, en el frasco "
        "entregado por el laboratorio.",
        None,
        None,
        (
            ConditionSeed(
                "PRIMERA_ORINA_HIGIENE",
                "Higiene genital previa",
                "higiene",
                "Lávese las manos y la zona genital con agua y jabón neutro; "
                "enjuague y seque bien antes de recoger la muestra.",
            ),
            ConditionSeed(
                "PRIMERA_ORINA_CHORRO",
                "Recolección de chorro medio",
                "recoleccion_muestra",
                "Elimine el primer chorro en el inodoro, recoja el chorro "
                "medio en el frasco y deseche el final. No toque el borde "
                "interno del frasco.",
            ),
            ConditionSeed(
                "PRIMERA_ORINA_ENTREGA",
                "Entrega oportuna",
                "recoleccion_muestra",
                "Entregue la muestra en el laboratorio dentro de las 2 horas "
                "siguientes a la recolección; si no es posible, manténgala "
                "refrigerada.",
                2,
                "horas",
            ),
        ),
    ),
    PreconditionSeed(
        "ORINA_24H",
        "Recolección de orina de 24 horas",
        "Recolección de todas las micciones durante un día completo para "
        "medir proteínas, creatinina u otros analitos en 24 horas.",
        "recoleccion_muestra",
        "Recolecte toda la orina de 24 horas en el recolector entregado "
        "por el laboratorio, siguiendo las instrucciones.",
        24,
        "horas",
        (
            ConditionSeed(
                "ORINA_24H_INICIO",
                "Descartar la primera orina del día",
                "recoleccion_muestra",
                "Al levantarse, orine y DESCARTE esa primera orina; anote la "
                "hora: ese es el inicio de la recolección.",
            ),
            ConditionSeed(
                "ORINA_24H_RECOLECCION",
                "Recoger todas las micciones siguientes",
                "recoleccion_muestra",
                "Durante las siguientes 24 horas recoja TODA la orina en el "
                "recolector, incluida la primera orina del día siguiente a "
                "la misma hora de inicio.",
                24,
                "horas",
            ),
            ConditionSeed(
                "ORINA_24H_REFRIGERACION",
                "Mantener refrigerado",
                "recoleccion_muestra",
                "Mantenga el recolector en la nevera o en un recipiente con "
                "hielo durante todo el período y no lo exponga al sol.",
            ),
            ConditionSeed(
                "ORINA_24H_LIQUIDOS",
                "Alimentación y líquidos habituales",
                "dieta",
                "Mantenga su dieta y la ingesta habitual de líquidos; no "
                "haga ejercicio extenuante durante la recolección.",
            ),
        ),
    ),
    PreconditionSeed(
        "SIN_BIOTINA",
        "Suspender biotina (vitamina B7)",
        "Dosis altas de biotina interfieren con inmunoensayos que usan "
        "estreptavidina-biotina (tiroides, hormonas, PSA, entre otros) y "
        "pueden dar resultados falsamente altos o bajos.",
        "medicamentos",
        "Suspenda los suplementos que contengan biotina durante las 72 "
        "horas previas a la toma de la muestra (consulte a su médico).",
        72,
        "horas",
        (
            ConditionSeed(
                "SIN_BIOTINA_SUPLEMENTOS",
                "Suplementos para cabello, piel y uñas",
                "medicamentos",
                "Multivitamínicos y suplementos capilares con biotina: "
                "suspender 48 horas antes.",
                48,
                "horas",
            ),
            ConditionSeed(
                "SIN_BIOTINA_DOSIS_ALTAS",
                "Dosis altas formuladas (5 mg o más al día)",
                "medicamentos",
                "Si su médico le formuló biotina en dosis altas, suspéndala "
                "72 horas antes solo con autorización médica.",
                72,
                "horas",
            ),
        ),
    ),
    PreconditionSeed(
        "RECOLECCION_HECES",
        "Recolección de heces",
        "Indicaciones para la recolección de materia fecal para examen "
        "coprológico, coproscópico y cultivo.",
        "recoleccion_muestra",
        "Recoja la muestra en el recolector entregado por el laboratorio, "
        "siguiendo las indicaciones.",
        None,
        None,
        (
            ConditionSeed(
                "RECOLECCION_HECES_LAXANTES",
                "Sin laxantes, aceites ni medios de contraste",
                "medicamentos",
                "No use laxantes ni aceite mineral en los 3 días previos, ni "
                "se haya hecho estudios con bario en la última semana.",
                3,
                "dias",
            ),
            ConditionSeed(
                "RECOLECCION_HECES_CONTAMINACION",
                "Evitar contaminación",
                "higiene",
                "Evacue en un recipiente limpio y seco (no directamente en el "
                "inodoro) y no mezcle las heces con orina, agua ni papel higiénico.",
            ),
            ConditionSeed(
                "RECOLECCION_HECES_ENTREGA",
                "Entrega oportuna",
                "recoleccion_muestra",
                "Entregue la muestra dentro de las 2 horas siguientes, o el "
                "mismo día si el recolector trae conservante o medio de transporte.",
                2,
                "horas",
            ),
        ),
    ),
    PreconditionSeed(
        "CORTISOL_MANANA",
        "Toma de cortisol en la mañana",
        "El cortisol tiene ritmo circadiano: su valor de referencia aplica "
        "a muestras de la mañana.",
        "horario_toma",
        "Acuda al laboratorio para la toma entre las 7:00 y las 9:00 a. m.",
        None,
        None,
        (
            ConditionSeed(
                "CORTISOL_REPOSO",
                "Reposo antes de la toma",
                "reposo",
                "Permanezca en reposo, sentado, 30 minutos antes de la toma.",
                30,
                "minutos",
            ),
            ConditionSeed(
                "CORTISOL_ESTRES",
                "Evitar estrés y esfuerzo",
                "actividad_fisica",
                "Evite el estrés intenso y el ejercicio la mañana de la toma "
                "y el día anterior.",
                24,
                "horas",
            ),
            ConditionSeed(
                "CORTISOL_CORTICOIDES",
                "Informar el uso de corticoides",
                "medicamentos",
                "Informe si usa corticoides (prednisona, dexametasona, "
                "cremas, inhaladores o inyecciones) o anticonceptivos "
                "orales; alteran el resultado.",
            ),
        ),
    ),
    PreconditionSeed(
        "PREPARACION_PSA",
        "Preparación para PSA (antígeno prostático)",
        "La actividad que estimula la próstata puede elevar falsamente el "
        "antígeno prostático específico.",
        "abstinencia_sexual",
        "Evite la eyaculación y el ciclismo durante las 48 horas previas a "
        "la toma de la muestra.",
        48,
        "horas",
        (
            ConditionSeed(
                "PSA_ABSTINENCIA",
                "Sin actividad sexual",
                "abstinencia_sexual",
                "No tenga relaciones sexuales ni eyaculación en las 48 horas previas.",
                48,
                "horas",
            ),
            ConditionSeed(
                "PSA_CICLISMO",
                "Sin ciclismo ni equitación",
                "actividad_fisica",
                "No monte bicicleta ni caballo en los 2 días previos.",
                48,
                "horas",
            ),
            ConditionSeed(
                "PSA_PROCEDIMIENTOS",
                "Sin tacto rectal ni procedimientos urológicos recientes",
                "otro",
                "Informe si le hicieron tacto rectal, biopsia, cistoscopia o "
                "sondaje en las últimas 6 semanas; la muestra debe tomarse "
                "antes de un tacto rectal.",
            ),
        ),
    ),
    PreconditionSeed(
        "ANTIBIOTICOS",
        "Informar el uso de antibióticos",
        "Los antibióticos pueden negativizar un cultivo; lo ideal es tomar "
        "la muestra antes de iniciarlos.",
        "medicamentos",
        "Informe si ha tomado antibióticos en los últimos 7 días; si es "
        "posible, tome la muestra antes de iniciar el tratamiento.",
        None,
        None,
        (
            ConditionSeed(
                "ANTIBIOTICOS_RECIENTES",
                "Antibióticos en la última semana",
                "medicamentos",
                "Indique el nombre del antibiótico y la fecha de la última "
                "dosis al personal de toma de muestras.",
                7,
                "dias",
            ),
        ),
    ),
)


async def load(api: DemoApi, registry: Registry) -> None:
    for precondition in PRECONDITIONS:
        created = await api.post(
            "/preconditions",
            {
                "code": precondition.code,
                "name": precondition.name,
                "description": precondition.description,
                "category": precondition.category,
                "duration_value": precondition.duration_value,
                "duration_unit": precondition.duration_unit,
                "patient_instructions": precondition.instructions,
            },
        )
        registry.preconditions[precondition.code] = created["id"]
        for item in precondition.items:
            created_item = await api.post(
                f"/preconditions/{created['id']}/items",
                {
                    "code": item.code,
                    "name": item.name,
                    "category": item.category,
                    "duration_value": item.duration_value,
                    "duration_unit": item.duration_unit,
                    "patient_instructions": item.instructions,
                },
            )
            registry.preconditions[item.code] = created_item["id"]
