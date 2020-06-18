from abc import ABC
from dataclasses import dataclass

from pylox.expr import Expr
from pylox.visitor import Visitable


class Stmt(Visitable, ABC):
    """Base class for Lox statements."""

    def __str__(self) -> str:
        return f"<{type(self).__name__}: {', '.join(str(attr) for attr in self.__dict__.values())}>"


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass
class PrintStmt(Stmt):
    expression: Expr


__all__ = ("Stmt", "ExpressionStmt", "PrintStmt",)
