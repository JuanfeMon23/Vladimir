"""Formulas de analitos `calculated`: gramatica segura, codigos validos de la
misma version, sin referencias circulares; se validan al guardar y al publicar.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.modules.result_templates import controller
from app.modules.result_templates.exceptions import (
    ResultTemplateVersionIncompleteError,
)
from app.modules.result_templates.formula import (
    FormulaNode,
    FormulaSyntaxError,
    formula_problems,
    parse_formula,
)
from app.modules.result_templates.models import Unit
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    ResultTemplateAnalyteCreate,
    ResultTemplateAnalyteUpdate,
    ResultTemplateCreate,
    ResultTemplateVersionCreate,
    ResultTemplateVersionRead,
)

# --- gramatica (funcion pura) ---


def test_parse_returns_referenced_codes_in_order_without_duplicates() -> None:
    assert parse_formula("GLU + HB * (TP - 2.5) / GLU") == ["GLU", "HB", "TP"]


def test_parse_accepts_braced_codes_with_any_character() -> None:
    assert parse_formula("{ZZanalyte-ab.c} * 2 + {X Y}") == ["ZZanalyte-ab.c", "X Y"]


def test_parse_accepts_unary_signs_numbers_and_nesting() -> None:
    assert parse_formula("-(A + +3) * 0.5") == ["A"]
    assert parse_formula("100 * (A / (B + 1))") == ["A", "B"]


def test_parse_literal_division_by_zero_is_syntactically_valid() -> None:
    assert parse_formula("A / 0") == ["A"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "A +",
        "* A",
        "A B",
        "A ** B",
        "(A",
        "A)",
        "()",
        "1..2",
        "A $ B",
        "__import__('os')",
        "A; B",
        "A if B else C",
        "A.attr",
        "{unclosed",
        "{}",
        "1e3 + A",
        "A % B",
    ],
)
def test_parse_rejects_anything_outside_the_grammar(text: str) -> None:
    with pytest.raises(FormulaSyntaxError):
        parse_formula(text)


def _nodes(**formulas: str | None) -> list[FormulaNode]:
    return [FormulaNode(code, formula, True) for code, formula in formulas.items()]


def test_problems_none_for_valid_formula() -> None:
    nodes = [*_nodes(A=None, B=None), FormulaNode("C", "A + B", True)]
    assert formula_problems(nodes[2], nodes) == []


def test_problems_detects_transitive_cycle_not_involving_the_node() -> None:
    nodes = _nodes(A="B", B="C", C="B")
    reasons = [p.reason for p in formula_problems(nodes[0], nodes)]
    assert reasons == ["cycle"]


def test_problems_ignores_syntax_errors_of_other_nodes_for_the_graph() -> None:
    nodes = _nodes(A="B", B="B +")
    assert formula_problems(nodes[0], nodes) == []


# --- controller ---


def _code() -> str:
    """Codigo que es identificador valido (sin llaves en la formula)."""
    return f"ZZ{uuid4().hex[:14]}"


async def _analyte(session: AsyncSession, code: str | None = None):
    return await controller.create_analyte(
        session, AnalyteCreate(code=code or _code(), name="Analito")
    )


async def _numeric(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit, code: str
):
    analyte = await _analyte(session, code)
    return await controller.create_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        ResultTemplateAnalyteCreate(
            analyte_id=analyte.id,
            sort_order=1,
            result_type="numeric",
            unit_id=unit.id,
            decimals=1,
            is_reportable=False,
        ),
    )


async def _calculated(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    unit: Unit,
    code: str,
    formula: str | None,
):
    analyte = await _analyte(session, code)
    return await controller.create_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        ResultTemplateAnalyteCreate(
            analyte_id=analyte.id,
            sort_order=2,
            result_type="calculated",
            unit_id=unit.id,
            decimals=2,
            formula=formula,
        ),
    )


async def _set_formula(session, draft, template_analyte, **fields):
    return await controller.update_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        ResultTemplateAnalyteUpdate(**fields),
    )


def _problems(error: ValidationAppError) -> list[dict]:
    return error.details["problems"]


async def test_create_calculated_with_valid_formula(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    a, b = _code(), _code()
    await _numeric(session, draft, unit, a)
    await _numeric(session, draft, unit, b)

    created = await _calculated(session, draft, unit, _code(), f"({a} + {b}) / 2")
    assert created.formula == f"({a} + {b}) / 2"


async def test_create_rejects_unknown_code(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        await _calculated(session, draft, unit, _code(), "NOEXISTE * 2")

    problem = _problems(exc_info.value)[0]
    assert problem["reason"] == "unknown_code"
    assert problem["codes"] == ["NOEXISTE"]
    assert exc_info.value.details["field"] == "formula"


async def test_create_rejects_code_of_another_version(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    unit: Unit,
    result_template_version_payload: dict,
) -> None:
    other_template = await controller.create_template(
        session, ResultTemplateCreate(code=_code(), name="Otra")
    )
    other_draft = await controller.create_version(
        session,
        other_template.id,
        ResultTemplateVersionCreate(**result_template_version_payload),
    )
    foreign = _code()
    await _numeric(session, other_draft, unit, foreign)

    with pytest.raises(ValidationAppError) as exc_info:
        await _calculated(session, draft, unit, _code(), f"{foreign} + 1")
    assert _problems(exc_info.value)[0]["reason"] == "unknown_code"


async def test_create_rejects_inactive_code(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    code = _code()
    numeric = await _numeric(session, draft, unit, code)
    await _set_formula(session, draft, numeric, is_active=False)

    with pytest.raises(ValidationAppError) as exc_info:
        await _calculated(session, draft, unit, _code(), f"{code} + 1")
    problem = _problems(exc_info.value)[0]
    assert problem["reason"] == "inactive_code"
    assert problem["codes"] == [code]


async def test_create_rejects_self_reference(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    code = _code()
    with pytest.raises(ValidationAppError) as exc_info:
        await _calculated(session, draft, unit, code, f"{code} * 2")
    assert _problems(exc_info.value)[0]["reason"] == "cycle"


async def test_update_rejects_cycle_between_calculated_analytes(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    base, a_code, b_code = _code(), _code(), _code()
    await _numeric(session, draft, unit, base)
    a = await _calculated(session, draft, unit, a_code, f"{base} + 1")
    await _calculated(session, draft, unit, b_code, f"{a_code} * 2")

    with pytest.raises(ValidationAppError) as exc_info:
        await _set_formula(session, draft, a, formula=f"{b_code} + 1")
    problem = _problems(exc_info.value)[0]
    assert problem["reason"] == "cycle"
    assert problem["codes"] == [a_code, b_code, a_code]

    # el rechazo no modifica lo guardado
    kept = await controller.list_template_analytes(
        session, draft.result_template_id, draft.id
    )
    assert next(t for t in kept if t.id == a.id).formula == f"{base} + 1"


async def test_create_rejects_invalid_syntax(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        await _calculated(session, draft, unit, _code(), "__import__('os')")
    assert _problems(exc_info.value)[0]["reason"] == "syntax"


async def test_update_without_touching_formula_does_not_revalidate(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_analyte = await _calculated(session, draft, unit, _code(), None)
    updated = await _set_formula(session, draft, template_analyte, sort_order=5)
    assert updated.sort_order == 5


# --- publicar ---


async def test_publish_valid_formula_succeeds(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    base = _code()
    await _numeric(session, draft, unit, base)
    await _calculated(session, draft, unit, _code(), f"{base} * 100")

    published = await controller.publish_version(
        session, draft.result_template_id, draft.id
    )
    assert published.status == "published"


async def test_publish_reports_invalid_formula_when_referenced_analyte_deactivated(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    base = _code()
    numeric = await _numeric(session, draft, unit, base)
    calculated = await _calculated(session, draft, unit, _code(), f"{base} * 100")
    await _set_formula(session, draft, numeric, is_active=False)

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await controller.publish_version(session, draft.result_template_id, draft.id)

    invalid = exc_info.value.details["invalid_formula"]
    assert len(invalid) == 1
    assert invalid[0]["template_analyte_id"] == str(calculated.id)
    assert invalid[0]["reason"] == "inactive_code"
    assert invalid[0]["codes"] == [base]
    assert exc_info.value.details["missing"] == []


async def test_publish_without_formula_problems_reports_empty_invalid_formula(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    await _calculated(session, draft, unit, _code(), None)

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await controller.publish_version(session, draft.result_template_id, draft.id)
    assert exc_info.value.details["invalid_formula"] == []
    assert exc_info.value.details["missing"][0]["missing_fields"] == ["formula"]


# --- HTTP ---


async def test_http_unknown_code_returns_422(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)

    response = await client.post(
        f"/api/v1/result-templates/{draft.result_template_id}"
        f"/versions/{draft.id}/analytes",
        json={
            "analyte_id": str(analyte.id),
            "sort_order": 1,
            "result_type": "calculated",
            "formula": "NOEXISTE + 1",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"]["problems"][0]["reason"] == "unknown_code"
