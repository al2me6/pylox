from abc import ABC
from itertools import repeat
from typing import List, Optional

from pylox.lox_types import LoxObject
from pylox.stmt import FunctionStmt, Stmt
from pylox.token import Token
from pylox.visitor import Visitable


class LoxCallable(Visitable, ABC):
    arity: int
    params: List[Token]
    body: Stmt

    def __repr__(self) -> str:
        return f"<function({', '.join(repeat('arg', self.arity))})>"


class LoxFunction(LoxCallable):
    def __init__(self, declaration: FunctionStmt) -> None:
        self.params = declaration.params
        self.arity = len(self.params)
        self.body = declaration.body


class LoxReturn(Exception):
    def __init__(self, value: Optional[LoxObject]) -> None:  # pylint: disable=super-init-not-called
        self.value = value
