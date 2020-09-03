from abc import ABC
from itertools import repeat
from typing import TYPE_CHECKING, Optional, Sequence

from pylox.language.lox_types import LoxIdentifier, LoxObject
from pylox.parsing.expr import AnonymousFunctionExpr, VariableExpr
from pylox.parsing.stmt import Stmt
from pylox.utilities.stacked_map import RawStack

if TYPE_CHECKING:
    from pylox.language.lox_class import LoxInstance


class LoxCallable(ABC):
    closure: RawStack[LoxIdentifier, LoxObject]
    arity: int
    params: Sequence[VariableExpr]
    body: Stmt

    def __repr__(self) -> str:
        return f"<function({', '.join(repeat('arg', self.arity))})>"


class LoxFunction(LoxCallable):
    def __init__(self, declaration: AnonymousFunctionExpr, closure: RawStack[LoxIdentifier, LoxObject]) -> None:
        self.params = declaration.params
        self.arity = len(self.params)
        self.body = declaration.body
        self.closure = closure
        self.bound_instance: Optional["LoxInstance"] = None
        self.kind = declaration.kind

    def bind_to_instance(self, instance: Optional["LoxInstance"]) -> "LoxFunction":
        self.bound_instance = instance
        return self


class LoxReturn(Exception):
    def __init__(self, value: Optional[LoxObject]) -> None:  # pylint: disable=super-init-not-called
        self.value = value
