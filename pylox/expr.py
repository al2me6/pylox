from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Union

from pylox.token import Token
from pylox.utilities import ast_node_pretty_printer
from pylox.visitor import Visitable

LoxLiteral = Union[float, str, bool, None]


class Expr(Visitable, ABC):
    """Base class for expressions which have differing attributes."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Expr")
        return f"({name} {' '.join(values)})"


@dataclass
class BinaryExpr(Expr):
    operator: Token
    left: Expr
    right: Expr

    def __str__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass
class GroupingExpr(Expr):
    expression: Expr


@dataclass
class LiteralExpr(Expr):
    value: LoxLiteral

    def __str__(self) -> str:
        if self.value is None:  # The null type is "nil" in Lox.
            return "nil"
        return str(self.value)


@dataclass
class UnaryExpr(Expr):
    operator: Token
    right: Expr


__all__ = ("LoxLiteral", "Expr", "BinaryExpr", "GroupingExpr", "LiteralExpr", "UnaryExpr",)
