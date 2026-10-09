"""Areas del laboratorio y sus encargados (con historial en 3 areas).

El flujo real de asignacion (`PUT /lab-areas/{id}/manager`) cierra la
asignacion vigente con `end_at = ahora` y abre la nueva en el mismo instante:
por eso el encargado ANTERIOR se asigna primero con un `start_at` pasado y el
actual despues sin `start_at` (queda `end_at` anterior == `start_at` actual).
"""

from datetime import UTC, datetime
from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class AreaSeed(NamedTuple):
    code: str
    name: str
    description: str
    manager: str  # document_number del encargado vigente
    previous_manager: str | None = None  # document_number del anterior
    previous_start: datetime | None = None


AREAS: tuple[AreaSeed, ...] = (
    AreaSeed(
        "HEM",
        "Hematología",
        "Análisis de las células de la sangre (hemograma completo, recuento de "
        "plaquetas) y estudios hematológicos básicos.",
        manager="79312458",
        previous_manager="71654309",
        previous_start=datetime(2022, 2, 1, 13, 0, tzinfo=UTC),
    ),
    AreaSeed(
        "QUI",
        "Química clínica",
        "Determinación de glucosa, lípidos, función renal y hepática, "
        "electrolitos y hemoglobina glicosilada en suero, plasma y orina.",
        manager="1017234580",
    ),
    AreaSeed(
        "INM",
        "Inmunología y serología",
        "Pruebas serológicas e inmunológicas: infecciones de transmisión "
        "sexual y hepatitis, marcadores inflamatorios y grupo sanguíneo.",
        manager="80453216",
    ),
    AreaSeed(
        "MIC",
        "Microbiología",
        "Cultivos (urocultivo, coprocultivo), identificación de "
        "microorganismos y pruebas de sensibilidad a antibióticos.",
        manager="1020456731",
        previous_manager="43275819",
        previous_start=datetime(2021, 6, 1, 13, 0, tzinfo=UTC),
    ),
    AreaSeed(
        "URO",
        "Uroanálisis",
        "Examen físico, químico y microscópico de orina, y pruebas en orina "
        "de 24 horas.",
        manager="1037612894",
    ),
    AreaSeed(
        "COA",
        "Coagulación",
        "Pruebas de hemostasia: tiempos de coagulación y fibrinógeno.",
        manager="43985120",
    ),
    AreaSeed(
        "PAR",
        "Parasitología y coprología",
        "Examen coprológico, coproscópico seriado y búsqueda de parásitos "
        "intestinales.",
        manager="1037612894",
    ),
    AreaSeed(
        "END",
        "Endocrinología y hormonas",
        "Hormonas tiroideas, cortisol, hormonas de la reproducción y "
        "marcadores tumorales por inmunoensayo.",
        manager="1128394057",
        previous_manager="52841907",
        previous_start=datetime(2022, 5, 2, 13, 0, tzinfo=UTC),
    ),
    AreaSeed(
        "TOM",
        "Toma de muestras",
        "Recepción de pacientes, venopunción, recolección y rotulado de "
        "muestras. No procesa exámenes propios.",
        manager="1152709463",
    ),
)


async def load(api: DemoApi, registry: Registry) -> None:
    for area in AREAS:
        created = await api.post(
            "/lab-areas",
            {"code": area.code, "name": area.name, "description": area.description},
        )
        registry.areas[area.code] = created["id"]
        if area.previous_manager is not None:
            assert area.previous_start is not None
            await api.put(
                f"/lab-areas/{created['id']}/manager",
                {
                    "staff_id": registry.staff[area.previous_manager],
                    "start_at": area.previous_start.isoformat(),
                    "notes": "Encargado inicial del área.",
                },
            )
        await api.put(
            f"/lab-areas/{created['id']}/manager",
            {
                "staff_id": registry.staff[area.manager],
                "notes": "Relevo en la jefatura del área."
                if area.previous_manager
                else "Encargado del área.",
            },
        )
