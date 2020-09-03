from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from pylox.language.lox_types import FunctionKind, LoxIdentifier, LoxPrimitive, lox_object_to_repr
from pylox.lexing.token import Token
from pylox.utilities import ast_node_pretty_printer

if TYPE_CHECKING:
    from pylox.parsing.stmt import GroupingDirective


class Expr:
    """Base class for expressions which have differing attributes."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Expr")
        return f"({name} {' '.join(values)})"


@dataclass
class AnonymousFunctionExpr(Expr):
    params: List["VariableExpr"]
    body: "GroupingDirective"
    kind: FunctionKind

    def __str__(self) -> str:
        params_text = ", ".join(param.target.lexeme for param in self.params)
        return f"(anonymousfunction [{params_text}], {self.body})"


@dataclass
class AssignmentExpr(Expr):
    target: Token
    value: Expr
    target_id: Optional[LoxIdentifier] = None


@dataclass
class DynamicAssignmentExpr(Expr):
    target: "AttributeAccessExpr"
    value: Expr


@dataclass
class AttributeAccessExpr(Expr):
    target: Expr
    attribute: Token


@dataclass
class BinaryExpr(Expr):
    operator: Token
    left: Expr
    right: Expr

    def __str__(self) -> str:
        return f"({self.operator.lexeme} {self.left} {self.right})"


@dataclass
class LogicalExpr(BinaryExpr):
    pass


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
class TernaryIfExpr(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Expr


@dataclass
class ThisExpr(Expr):
    keyword: Token


@dataclass
class UnaryExpr(Expr):
    operator: Token
    right: Expr

    def __str__(self) -> str:
        return f"({self.operator.lexeme} {self.right})"


@dataclass
class VariableExpr(Expr):
    target: Token
    target_id: Optional[LoxIdentifier] = None
