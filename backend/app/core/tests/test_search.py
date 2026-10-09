"""Tests de la busqueda `?q=` del nucleo (`SearchFilter`) y de su uso en
todos los listados paginados de la API."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import SearchFilter
from app.modules.consent_documents.models import ConsentDocument
from app.modules.lab_areas.models import LabArea
from app.modules.lab_tests.models import LabTest
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabel
from app.modules.result_templates.models import (
    Analyte,
    ResultOption,
    ResultOptionSet,
    ResultTemplate,
    Unit,
)
from app.modules.samples.models import Sample, SampleType
from app.modules.staff.models import Staff

# --------------------------------------------------------------------------
# SearchFilter (unidad)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [None, "", "   ", "\t \n"])
def test_sin_texto_no_hay_terminos(raw: str | None) -> None:
    assert SearchFilter(q=raw).terms == []


def test_terminos_recortan_y_colapsan_espacios() -> None:
    assert SearchFilter(q="  hemo   grama \t").terms == ["hemo", "grama"]


def test_maximo_8_palabras() -> None:
    assert len(SearchFilter(q=" ".join("abcdefghijkl")).terms) == 8


def test_apply_sin_texto_devuelve_el_mismo_stmt() -> None:
    stmt = select(LabArea)
    assert SearchFilter(q="  ").apply(stmt, LabArea.name) is stmt


def test_apply_escapa_comodines() -> None:
    sql = str(SearchFilter(q="50%_\\").apply(select(LabArea), LabArea.name).compile())
    assert "LIKE" in sql and "ESCAPE" in sql


# --------------------------------------------------------------------------
# SearchFilter contra la BD (LabArea: code, name)
# --------------------------------------------------------------------------


def _token() -> str:
    return f"zq{uuid4().hex[:12]}"


async def _areas(session: AsyncSession, token: str, *names: str) -> list[LabArea]:
    rows = [
        LabArea(code=f"{token}-{i}", name=name) for i, name in enumerate(names, start=1)
    ]
    session.add_all(rows)
    await session.commit()
    return rows


async def _search(session: AsyncSession, q: str) -> set[str]:
    stmt = SearchFilter(q=q).apply(select(LabArea), LabArea.code, LabArea.name)
    return {row.name for row in (await session.execute(stmt)).scalars()}


async def test_ignora_mayusculas_y_tildes(session: AsyncSession) -> None:
    token = _token()
    await _areas(session, token, f"Hematología {token}")

    assert await _search(session, f"HEMATOLOGIA {token.upper()}") == {
        f"Hematología {token}"
    }
    assert await _search(session, f"hematología {token}") == {f"Hematología {token}"}


async def test_multi_palabra_es_and_entre_palabras_y_or_entre_columnas(
    session: AsyncSession,
) -> None:
    token = _token()
    await _areas(session, token, f"Alfa Beta {token}", f"Alfa Gamma {token}")

    assert await _search(session, f"alfa {token}") == {
        f"Alfa Beta {token}",
        f"Alfa Gamma {token}",
    }
    assert await _search(session, f"beta {token}") == {f"Alfa Beta {token}"}
    # una palabra en `code` y otra en `name` (AND entre palabras, OR entre columnas)
    assert await _search(session, f"{token}-1 gamma") == set()
    assert await _search(session, f"{token}-2 gamma") == {f"Alfa Gamma {token}"}


@pytest.mark.parametrize("wildcard", ["%", "_", "\\", "%%", "a%"])
async def test_los_comodines_se_buscan_literalmente(
    session: AsyncSession, wildcard: str
) -> None:
    token = _token()
    await _areas(session, token, f"Plano {token}", f"Con {wildcard} {token}")

    found = await _search(session, f"{wildcard} {token}")

    assert found <= {f"Con {wildcard} {token}"}
    assert f"Plano {token}" not in found


async def test_comillas_no_inyectan_sql(session: AsyncSession) -> None:
    token = _token()
    await _areas(session, token, f"Normal {token}")

    assert await _search(session, "'; DROP TABLE lab_areas; --") == set()
    assert await _search(session, f'" OR 1=1 -- {token}') == set()
    assert await _search(session, f"normal {token}") == {f"Normal {token}"}


# --------------------------------------------------------------------------
# Todos los listados paginados aceptan `?q=`
# --------------------------------------------------------------------------

Factory = Callable[[AsyncSession, str, bool], Awaitable[str]]
"""`(session, texto, activo) -> path del listado`; el texto va en la columna
buscada del caso."""


def _simple(model, column: str, path: str, **fixed) -> Factory:
    async def make(session: AsyncSession, text: str, active: bool) -> str:
        values = {"code": f"zz-{uuid4().hex[:16]}", "name": "Fila", **fixed}
        values[column] = text
        session.add(model(is_active=active, **values))
        await session.commit()
        return path

    return make


async def _lab_test(session: AsyncSession, text: str, active: bool) -> str:
    area = LabArea(code=f"zz-{uuid4().hex[:16]}", name="Area")
    session.add(area)
    await session.flush()
    session.add(
        LabTest(
            code=f"zz-{uuid4().hex[:16]}", name=text, area_id=area.id, is_active=active
        )
    )
    await session.commit()
    return "/api/v1/lab-tests"


async def _staff(session: AsyncSession, text: str, active: bool) -> str:
    session.add(
        Staff(
            document_type="CC",
            document_number=f"zz{uuid4().hex[:16]}",
            first_name="Nombre",
            last_name=text,
            is_active=active,
        )
    )
    await session.commit()
    return "/api/v1/staff"


async def _sample_type(session: AsyncSession, text: str, active: bool) -> str:
    sample = Sample(code=f"zz-{uuid4().hex[:16]}", name="Muestra")
    session.add(sample)
    await session.flush()
    session.add(
        SampleType(
            code=f"zz-{uuid4().hex[:16]}",
            name=text,
            sample_id=sample.id,
            specimen="suero",
            is_active=active,
        )
    )
    await session.commit()
    return f"/api/v1/samples/{sample.id}/types"


async def _option(session: AsyncSession, text: str, active: bool) -> str:
    option_set = ResultOptionSet(code=f"zz-{uuid4().hex[:16]}", name="Conjunto")
    session.add(option_set)
    await session.flush()
    session.add(
        ResultOption(
            option_set_id=option_set.id,
            code="op",
            label=text,
            sort_order=1,
            is_active=active,
        )
    )
    await session.commit()
    return f"/api/v1/result-option-sets/{option_set.id}/options"


async def _precondition(session: AsyncSession, text: str, active: bool) -> str:
    session.add(
        Precondition(
            code=f"zz-{uuid4().hex[:16]}",
            name=text,
            kind="precondition",
            category="ayuno",
            is_active=active,
        )
    )
    await session.commit()
    return "/api/v1/preconditions"


SEARCH_CASES: list[tuple[str, Factory]] = [
    ("/staff:last_name", _staff),
    ("/lab-areas:name", _simple(LabArea, "name", "/api/v1/lab-areas")),
    ("/lab-areas:code", _simple(LabArea, "code", "/api/v1/lab-areas")),
    ("/lab-tests:name", _lab_test),
    ("/preconditions:name", _precondition),
    ("/samples:name", _simple(Sample, "name", "/api/v1/samples")),
    ("/samples/{id}/types:name", _sample_type),
    ("/print-labels:name", _simple(PrintLabel, "name", "/api/v1/print-labels")),
    (
        "/consent-documents:name",
        _simple(
            ConsentDocument,
            "name",
            "/api/v1/consent-documents",
            document_type="otro",
        ),
    ),
    (
        "/result-templates:name",
        _simple(ResultTemplate, "name", "/api/v1/result-templates"),
    ),
    ("/analytes:name", _simple(Analyte, "name", "/api/v1/analytes")),
    (
        "/analytes:loinc_code",
        _simple(Analyte, "loinc_code", "/api/v1/analytes"),
    ),
    (
        "/result-option-sets:name",
        _simple(ResultOptionSet, "name", "/api/v1/result-option-sets"),
    ),
    ("/units:symbol", _simple(Unit, "symbol", "/api/v1/units")),
    ("/units:name", _simple(Unit, "name", "/api/v1/units", symbol="u")),
    ("/result-option-sets/{id}/options:label", _option),
]


@pytest.mark.parametrize(
    "factory", [c[1] for c in SEARCH_CASES], ids=[c[0] for c in SEARCH_CASES]
)
async def test_listado_con_q_filtra_total_y_combina_con_active(
    client: AsyncClient, session: AsyncSession, factory: Factory
) -> None:
    token = _token()
    # `loinc_code`/`symbol` son cortos (32): el texto debe caber en ellos.
    text = f"Ácido {token}"
    path = await factory(session, text, True)

    response = await client.get(path, params={"q": f"ACIDO {token.upper()}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1

    # `active=false` no encuentra la fila activa; sin coincidencia, total 0
    only_inactive = await client.get(
        path, params={"q": f"acido {token}", "active": "false"}
    )
    assert only_inactive.json()["total"] == 0
    nothing = await client.get(path, params={"q": f"zzzz{token}"})
    assert nothing.json()["total"] == 0


async def test_q_vacio_devuelve_todo_y_comodin_no_devuelve_todo(
    client: AsyncClient, session: AsyncSession
) -> None:
    token = _token()
    await _areas(session, token, f"Uno {token}", f"Dos {token}")
    everything = (await client.get("/api/v1/lab-areas")).json()["total"]

    blank = (await client.get("/api/v1/lab-areas", params={"q": "  "})).json()
    percent = (await client.get("/api/v1/lab-areas", params={"q": "%"})).json()

    assert blank["total"] == everything
    assert percent["total"] < everything


async def test_q_se_combina_con_paginacion_y_total_refleja_el_filtro(
    client: AsyncClient, session: AsyncSession
) -> None:
    token = _token()
    await _areas(session, token, *[f"Area {n} {token}" for n in range(5)])

    page = (
        await client.get(
            "/api/v1/lab-areas", params={"q": token, "page": 2, "page_size": 2}
        )
    ).json()

    assert page["total"] == 5
    assert len(page["items"]) == 2


async def test_q_mayor_a_100_caracteres_es_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/lab-areas", params={"q": "a" * 101})
    assert response.status_code == 422


async def test_openapi_documenta_q_en_cada_listado(client: AsyncClient) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    expected = {
        "/api/v1/staff",
        "/api/v1/lab-areas",
        "/api/v1/lab-tests",
        "/api/v1/preconditions",
        "/api/v1/samples",
        "/api/v1/samples/{sample_id}/types",
        "/api/v1/print-labels",
        "/api/v1/consent-documents",
        "/api/v1/result-templates",
        "/api/v1/analytes",
        "/api/v1/result-option-sets",
        "/api/v1/result-option-sets/{option_set_id}/options",
        "/api/v1/units",
    }
    for path in expected:
        params = {p["name"]: p for p in paths[path]["get"]["parameters"]}
        assert "q" in params, path
        assert "sin distinguir" in params["q"]["description"], path
        assert params["q"]["schema"]["anyOf"][0]["maxLength"] == 100
