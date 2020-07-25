from abc import ABC
from dataclasses import dataclass
from typing import List, Optional

from pylox.language.lox_types import LoxIdentifier, LoxPrimitive, lox_object_to_repr
from pylox.lexing.token import Token
from pylox.utilities import ast_node_pretty_printer
from pylox.utilities.visitor import Visitable


class Expr(Visitable, ABC):
    """Base class for expressions which have differing attributes."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Expr")
        return f"({name} {' '.join(values)})"


@dataclass
class AssignmentExpr(Expr):
    name: Token
    mangled: Optional[LoxIdentifier]
    value: Expr


@dataclass
class BinaryExpr(Expr):
    operator: Token
    left: Expr
    right: Expr

    def __str__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass
class CallExpr(Expr):
    callee: Expr
    paren: Token
    arguments: List[Expr]

    def __str__(self) -> str:
        return f"(call {self.callee} [{', '.join(map(str, self.arguments))}])"


@dataclass
class GroupingExpr(Expr):
    expression: Expr


@dataclass
class LiteralExpr(Expr):
    value: LoxPrimitive

    def __str__(self) -> str:
        return lox_object_to_repr(self.value)


@dataclass
class LogicalExpr(BinaryExpr):
    pass


@dataclass
class TernaryIfExpr(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Expr


@dataclass
class UnaryExpr(Expr):
    operator: Token
    right: Expr

    def __str__(self) -> str:
        return f"({self.operator.lexeme} {self.right})"


@dataclass
class VariableExpr(Expr):
    name: Token
    mangled: Optional[LoxIdentifier]
