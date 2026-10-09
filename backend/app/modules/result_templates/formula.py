"""Formulas de los analitos `calculated`: gramatica minima y validacion.

Gramatica (analizador propio, nunca `eval`):

    expr    := term (("+" | "-") term)*
    term    := unary (("*" | "/") unary)*
    unary   := ("+" | "-") unary | primary
    primary := NUMBER | CODE | "(" expr ")"
    NUMBER  := digitos ("." digitos)?          p. ej. 100, 0.5
    CODE    := [A-Za-z_][A-Za-z0-9_]*          codigo de analito "simple"
             | "{" cualquier caracter salvo llaves "}"   cualquier otro codigo
                                               (p. ej. {ALT-TGP})

Los espacios se ignoran. Todo lo demas (exponentes, `%`, funciones,
comparaciones, atributos, comillas...) es error de sintaxis. Los
identificadores son `code` de analitos (`analytes.code`, sensible a
mayusculas). La division por un cero literal es sintacticamente valida (el
valor depende del resultado en tiempo de captura, no de la plantilla).

`formula_problems` valida una formula contra los analitos de UNA version:
solo pueden referenciarse analitos ACTIVOS de esa misma version y no puede
haber referencias circulares (DFS sobre las formulas de la version).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

FormulaProblemReason = Literal["syntax", "unknown_code", "inactive_code", "cycle"]

_MAX_DEPTH = 50
_TOKEN = re.compile(
    r"""
    \s*(?:
        (?P<number>\d+(?:\.\d+)?)
      | (?P<code>[A-Za-z_][A-Za-z0-9_]*)
      | \{(?P<braced>[^{}]*)\}
      | (?P<op>[-+*/()])
    )
    """,
    re.VERBOSE,
)


class FormulaSyntaxError(ValueError):
    """La formula no cumple la gramatica (mensaje en espanol)."""


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        match = _TOKEN.match(text, pos)
        if match is None:
            offset = pos + len(text[pos:]) - len(text[pos:].lstrip())
            raise FormulaSyntaxError(
                f"carácter no permitido «{text[offset]}» en la posición {offset + 1}"
            )
        kind = match.lastgroup or ""
        value = match.group(kind)
        if kind == "braced" and not value.strip():
            raise FormulaSyntaxError("hay un código vacío entre llaves")
        tokens.append((kind, value))
        pos = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.index = 0
        self.depth = 0
        self.codes: list[str] = []

    def _peek(self) -> tuple[str, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _peek_op(self, *ops: str) -> str | None:
        token = self._peek()
        if token is not None and token[0] == "op" and token[1] in ops:
            return token[1]
        return None

    def parse(self) -> list[str]:
        if not self.tokens:
            raise FormulaSyntaxError("la fórmula está vacía")
        self._expr()
        leftover = self._peek()
        if leftover is not None:
            raise FormulaSyntaxError(
                f"se esperaba un operador antes de «{leftover[1]}»"
            )
        return self.codes

    def _enter(self) -> None:
        self.depth += 1
        if self.depth > _MAX_DEPTH:
            raise FormulaSyntaxError("la fórmula tiene demasiados niveles anidados")

    def _expr(self) -> None:
        self._enter()
        self._term()
        while self._peek_op("+", "-"):
            self.index += 1
            self._term()
        self.depth -= 1

    def _term(self) -> None:
        self._unary()
        while self._peek_op("*", "/"):
            self.index += 1
            self._unary()

    def _unary(self) -> None:
        if self._peek_op("+", "-"):
            self.index += 1
            self._enter()
            self._unary()
            self.depth -= 1
            return
        self._primary()

    def _primary(self) -> None:
        token = self._peek()
        if token is None:
            raise FormulaSyntaxError("la fórmula termina antes de tiempo")
        kind, value = token
        if kind in ("number", "code", "braced"):
            self.index += 1
            if kind != "number" and value not in self.codes:
                self.codes.append(value)
            return
        if value == "(":
            self.index += 1
            self._expr()
            if not self._peek_op(")"):
                raise FormulaSyntaxError("falta cerrar un paréntesis")
            self.index += 1
            return
        raise FormulaSyntaxError(f"no se esperaba «{value}» en ese lugar")


def parse_formula(text: str) -> list[str]:
    """Valida la sintaxis y devuelve los codigos referenciados (sin repetir,
    en orden de aparicion). Lanza `FormulaSyntaxError`."""
    return _Parser(_tokenize(text)).parse()


@dataclass(frozen=True)
class FormulaNode:
    """Un analito de la version: su codigo, su formula (o `None`) y si esta
    activo (la fila de la version y el analito del catalogo)."""

    code: str
    formula: str | None
    is_active: bool


@dataclass(frozen=True)
class FormulaProblem:
    reason: FormulaProblemReason
    message: str
    codes: list[str]

    def as_dict(self) -> dict:
        return {"reason": self.reason, "message": self.message, "codes": self.codes}


def _references(formula: str | None) -> list[str]:
    if formula is None:
        return []
    try:
        return parse_formula(formula)
    except FormulaSyntaxError:
        return []


def _find_cycle(graph: dict[str, list[str]], start: str) -> list[str] | None:
    """DFS desde `start`: el primer ciclo alcanzable, como ruta cerrada
    (`[A, B, A]`), o `None`."""
    visiting: list[str] = []
    done: set[str] = set()

    def visit(code: str) -> list[str] | None:
        if code in visiting:
            return [*visiting[visiting.index(code) :], code]
        if code in done:
            return None
        visiting.append(code)
        for nxt in graph.get(code, ()):
            cycle = visit(nxt)
            if cycle is not None:
                return cycle
        visiting.pop()
        done.add(code)
        return None

    return visit(start)


def formula_problems(
    node: FormulaNode, nodes: Iterable[FormulaNode]
) -> list[FormulaProblem]:
    """Problemas de la formula de `node` (vacia = valida). `nodes` son TODOS
    los analitos de la version (activos e inactivos) e incluyen a `node`."""
    nodes = list(nodes)
    try:
        refs = parse_formula(node.formula or "")
    except FormulaSyntaxError as error:
        return [FormulaProblem("syntax", f"Sintaxis inválida: {error}.", [])]

    active = {n.code for n in nodes if n.is_active}
    known = {n.code for n in nodes}
    problems: list[FormulaProblem] = []

    unknown = sorted(code for code in refs if code not in known)
    if unknown:
        problems.append(
            FormulaProblem(
                "unknown_code",
                "La fórmula usa códigos que no son analitos de esta versión: "
                f"{', '.join(unknown)}.",
                unknown,
            )
        )
    inactive = sorted(code for code in refs if code in known and code not in active)
    if inactive:
        problems.append(
            FormulaProblem(
                "inactive_code",
                f"La fórmula usa analitos inactivos: {', '.join(inactive)}.",
                inactive,
            )
        )

    graph = {n.code: _references(n.formula) for n in nodes if n.is_active}
    graph[node.code] = refs
    cycle = _find_cycle(graph, node.code)
    if cycle is not None:
        problems.append(
            FormulaProblem(
                "cycle",
                f"La fórmula tiene una referencia circular: {' → '.join(cycle)}.",
                cycle,
            )
        )
    return problems
