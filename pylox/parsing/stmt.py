from dataclasses import dataclass
from typing import List, Optional

from pylox.language.lox_types import LoxIdentifier
from pylox.lexing.token import Token
from pylox.parsing.expr import Expr
from pylox.utilities import ast_node_pretty_printer, indent


class Stmt:
    """Base class for Lox statements."""

    def __str__(self) -> str:
        name, values = ast_node_pretty_printer(self, "Stmt")
        return f"<{name}: {', '.join(values)}>"


class GroupingDirective(Stmt):
    """An un-scoped group of statements."""
    body: List[Stmt]

    def __init__(self, *body: Stmt) -> None:
        self.body = list(body)

    def __str__(self) -> str:
        inner_text = "".join(indent(str(stmt)) for stmt in self.body)
        return f"<{type(self).__name__.lower().replace('stmt', '')}:\n{inner_text}>"


class BlockStmt(GroupingDirective):
    """A block statement that is evaluated in its own scope."""

    def __init__(self, *body: Stmt) -> None:
        # Flatten out multiple levels of blocks. A block immediately enclosing another
        # is functionally equivalent to a single block.
        if len(body) == 1 and issubclass(type(body[0]), GroupingDirective):
            self.body = body[0].body  # type: ignore
        else:
            super().__init__(*body)

@dataclass
class ClassDeclarationStmt(Stmt):
    name: Token
    instance_variables: List["VariableDeclarationStmt"]
    uniq_id: Optional[LoxIdentifier] = None

    def __str__(self) -> str:
        body_text = "".join(indent(str(stmt)) for stmt in self.instance_variables)
        return f"<{type(self).__name__.lower().replace('stmt', '')}: {self.name}\n{indent(body_text)}\n{self.uniq_id}>"


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
class ReturnStmt(Stmt):
    keyword: Token
    expression: Optional[Expr]


@dataclass
class VariableDeclarationStmt(Stmt):
    ident: Token
    initializer: Optional[Expr]
    uniq_id: Optional[LoxIdentifier] = None


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt
