from abc import ABC
from itertools import repeat
from typing import Optional, Sequence

from pylox.language.lox_types import LoxIdentifier, LoxObject
from pylox.parsing.expr import VariableExpr
from pylox.parsing.stmt import FunctionDeclarationStmt, Stmt
from pylox.runtime.stacked_map import RawStack


class LoxCallable(ABC):
    environment: RawStack[LoxIdentifier, LoxObject]
    arity: int
    params: Sequence[VariableExpr]
    body: Stmt

    def __repr__(self) -> str:
        return f"<function({', '.join(repeat('arg', self.arity))})>"


class LoxFunction(LoxCallable):
    def __init__(self, declaration: FunctionDeclarationStmt, frame: RawStack[LoxIdentifier, LoxObject]) -> None:
        self.params = declaration.params
        self.arity = len(self.params)
        self.body = declaration.body
        self.environment = frame


class LoxReturn(Exception):
    def __init__(self, value: Optional[LoxObject]) -> None:  # pylint: disable=super-init-not-called
        self.value = value
