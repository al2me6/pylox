from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Union

from pylox.token import Token
from pylox.visitor import Visitable, Visitor

LoxLiteral = Union[float, str, bool, None]


class Expr(Visitor, Visitable, ABC):
    """Base class for expressions which have differing attributes.

    Implements Visitor<Expr> for production of nice debug output.
    """

    # pylint: disable=invalid-name

    def _visit_BinaryExpr__(self, expr: BinaryExpr) -> str:
        return self._render(expr.operator.lexeme, expr.left, expr.right)

    def _visit_GroupingExpr__(self, expr: GroupingExpr) -> str:
        return self._render("group", expr.expression)

    def _visit_LiteralExpr__(self, expr: LiteralExpr) -> str:
        if expr.value is None:  # the null type is "nil" in Lox
            return "nil"
        return str(expr.value)

    def _visit_UnaryExpr__(self, expr: UnaryExpr) -> str:
        return self._render(expr.operator.lexeme, expr.right)

    def _render(self, name: str, *exprs: Expr) -> str:
        # recursively render sub-expressions
        sub_expressions = " ".join(expr.accept(self) for expr in exprs)
        return f"({' '.join((name, sub_expressions))})"

    def __str__(self) -> str:
        try:
            return self.accept(self)  # accepting an Expr triggers rendering
        except NotImplementedError:
            return repr(self)


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: Token
    right: Expr


@dataclass
class GroupingExpr(Expr):
    expression: Expr


@dataclass
class LiteralExpr(Expr):
    value: LoxLiteral


@dataclass
class UnaryExpr(Expr):
    operator: Token
    right: Expr


__all__ = ("LoxLiteral", "Expr", "BinaryExpr", "GroupingExpr", "LiteralExpr", "UnaryExpr",)
