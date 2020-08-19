from abc import ABC
from itertools import repeat
from typing import List, Optional

from pylox.language.lox_types import LoxIdentifier, LoxObject
from pylox.parsing.expr import VariableExpr
from pylox.parsing.stmt import FunctionStmt, Stmt
from pylox.runtime.stacked_map import RawStack
from pylox.utilities.visitor import Visitable


class LoxCallable(Visitable, ABC):
    arity: int
    params: List[VariableExpr]
    body: Stmt
    environment: RawStack[LoxIdentifier, LoxObject]

    def __repr__(self) -> str:
        return f"<function({', '.join(repeat('arg', self.arity))})>"


class LoxFunction(LoxCallable):
    def __init__(self, declaration: FunctionStmt, frame: RawStack[LoxIdentifier, LoxObject]) -> None:
        self.params = declaration.params
        self.arity = len(self.params)
        self.body = declaration.body
        self.environment = frame


class LoxReturn(Exception):
    def __init__(self, value: Optional[LoxObject]) -> None:  # pylint: disable=super-init-not-called
        self.value = value
