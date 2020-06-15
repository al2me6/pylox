from abc import ABC
from dataclasses import dataclass

from pylox.expr import Expr
from pylox.visitor import Visitable

__all__ = ("Stmt", "ExpressionStmt", "PrintStmt",)


class Stmt(Visitable, ABC):
    """Base class for Lox statements"""


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass
class PrintStmt(Stmt):
    expression: Expr
