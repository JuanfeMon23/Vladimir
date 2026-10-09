"""Personal del laboratorio (datos INVENTADOS: nombres, cedulas, correos y
telefonos son ficticios; los correos usan el TLD reservado `.example`).

Es el unico bloque de la demostracion que no representa datos reales.
"""

from typing import NamedTuple

from app.core.db.seeds.demo.client import DemoApi
from app.core.db.seeds.demo.registry import Registry


class StaffSeed(NamedTuple):
    document_type: str
    document_number: str
    first_name: str
    last_name: str
    email: str
    phone: str
    job_title: str
    professional_license: str | None


def _email(first: str, last: str) -> str:
    plain = (first + "." + last.split()[0]).lower()
    for src, dst in zip("áéíóúñ", "aeioun", strict=True):
        plain = plain.replace(src, dst)
    return f"{plain.replace(' ', '')}@laboratorio-demo.example"


_PEOPLE = (
    (
        "52841907",
        "Laura Marcela",
        "Quintero Ospina",
        "Bacterióloga - Directora técnica",
        "BAC-24817",
        "3104567812",
    ),
    (
        "79312458",
        "Andrés Felipe",
        "Mejía Cardona",
        "Bacteriólogo - Jefe de Hematología",
        "BAC-19342",
        "3115023491",
    ),
    (
        "1017234580",
        "Diana Carolina",
        "Restrepo Giraldo",
        "Bacterióloga - Jefa de Química clínica",
        "BAC-31205",
        "3207785620",
    ),
    (
        "80453216",
        "Camilo Ernesto",
        "Valencia Parra",
        "Bacteriólogo - Jefe de Inmunología y serología",
        "BAC-22761",
        "3012349087",
    ),
    (
        "1020456731",
        "Natalia Andrea",
        "Salazar Duque",
        "Bacterióloga - Jefa de Microbiología",
        "BAC-35519",
        "3186620045",
    ),
    (
        "1037612894",
        "Sebastián",
        "Orozco Betancur",
        "Técnico de laboratorio - Uroanálisis y coprología",
        None,
        "3153308716",
    ),
    (
        "43985120",
        "Paola Andrea",
        "Rincón Zapata",
        "Bacterióloga - Jefa de Coagulación",
        "BAC-27034",
        "3224481950",
    ),
    (
        "1128394057",
        "Julián David",
        "Herrera Ocampo",
        "Bacteriólogo - Jefe de Endocrinología",
        "BAC-33870",
        "3009157263",
    ),
    (
        "1152709463",
        "Mónica Patricia",
        "Arango Henao",
        "Auxiliar de laboratorio - Toma de muestras",
        None,
        "3176094428",
    ),
    (
        "71654309",
        "Carlos Eduardo",
        "Londoño Vélez",
        "Técnico de laboratorio - Hematología",
        None,
        "3138820571",
    ),
    (
        "1010562378",
        "Yurany Alejandra",
        "Cifuentes Marín",
        "Auxiliar administrativa",
        None,
        "3217764093",
    ),
    (
        "98764512",
        "Ricardo Alonso",
        "Peña Gómez",
        "Administrador de sede",
        None,
        "3101938654",
    ),
    (
        "43275819",
        "Sandra Milena",
        "Triana Cruz",
        "Bacterióloga - Microbiología",
        "BAC-18456",
        "3195527306",
    ),
)

STAFF: tuple[StaffSeed, ...] = tuple(
    StaffSeed("CC", doc, first, last, _email(first, last), phone, title, license_number)
    for doc, first, last, title, license_number, phone in _PEOPLE
)


def staff_payload(person: StaffSeed) -> dict:
    return {
        "document_type": person.document_type,
        "document_number": person.document_number,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "email": person.email,
        "phone": person.phone,
        "job_title": person.job_title,
        "professional_license": person.professional_license,
    }


async def load(api: DemoApi, registry: Registry) -> None:
    for person in STAFF:
        created = await api.post("/staff", staff_payload(person))
        registry.staff[person.document_number] = created["id"]
