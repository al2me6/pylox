from abc import ABC
from dataclasses import dataclass

from pylox.expr import Expr
from pylox.token import Token
from pylox.utilities import ast_node_pretty_printer
from pylox.visitor import Visitable


class Stmt(Visitable, ABC):
    """Base class for Lox statements."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Stmt")
        return f"<{name}: {', '.join(values)}>"


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass
class PrintStmt(Stmt):
    expression: Expr


__all__ = ("Stmt", "ExpressionStmt", "PrintStmt",)
