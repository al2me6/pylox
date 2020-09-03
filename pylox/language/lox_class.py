from abc import ABC
from typing import Dict, Optional

from pylox.language.lox_callable import LoxCallable, LoxFunction
from pylox.language.lox_types import LoxIdentifier, LoxObject
from pylox.lexing.token import Token
from pylox.utilities.stacked_map import RawStack


class DynamicallyResolved(ABC):
    variables: Dict[str, LoxObject]

    def get(self, ident: str) -> LoxObject:
        return self.variables[ident]

    def set(self, ident: str, value: LoxObject) -> bool:
        is_overwrite = ident in self.variables
        self.variables[ident] = value
        return is_overwrite


class LoxClass(LoxCallable, DynamicallyResolved):
    constructor: Optional[LoxFunction] = None

    def __init__(
            self,
            name: Token,
            fields: Dict[str, LoxObject],
            closure: RawStack[LoxIdentifier, LoxObject]
    ) -> None:
        self.name = name
        self.variables = fields
        self.closure = closure

        if constructor := self.variables.get("init"):
            assert isinstance(constructor, LoxFunction)
            constructor.is_constructor = True
            self.params = constructor.params
            self.arity = constructor.arity
            self.constructor = constructor
        else:
            self.params = ()
            self.arity = 0

    def __repr__(self) -> str:
        return self.name.lexeme


class LoxInstance(DynamicallyResolved):
    def __init__(self, lox_class: LoxClass) -> None:
        self._class = lox_class
        self.variables = dict()


    def get(self, ident: str) -> LoxObject:
        if ident in self.variables:
            return super().get(ident)
        resolved = self._class.get(ident)
        if isinstance(resolved, LoxFunction):
            resolved.bind_to_instance(self)
        return resolved

    def __str__(self) -> str:
        return f"{self._class.name.lexeme} instance"
