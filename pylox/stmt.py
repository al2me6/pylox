from abc import ABC
from dataclasses import dataclass
from typing import List, Optional

from pylox.expr import Expr
from pylox.token import Token
from pylox.utilities import ast_node_pretty_printer, indent
from pylox.visitor import Visitable


class Stmt(Visitable, ABC):
    """Base class for Lox statements."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Stmt")
        return f"<{name}: {', '.join(values)}>"


@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]

    def __str__(self) -> str:
        inner_text = "".join(indent(str(stmt)) for stmt in self.statements)
        return f"<block:\n{inner_text}>"


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]

    def __str__(self) -> str:
        inner_text = "".join(indent(str(attr)) for attr in vars(self).values())
        return f"<if:\n{inner_text}>"


@dataclass
class PrintStmt(Stmt):
    expression: Expr


@dataclass
class VarStmt(Stmt):
    name: Token
    initializer: Optional[Expr]


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt
