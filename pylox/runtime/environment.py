from __future__ import annotations

from typing import Dict, Optional

from pylox.utilities.error import LoxRuntimeError
from pylox.language.lox_types import LoxObject
from pylox.lexing.token import Token


class Environment:
    def __init__(self, enclosing: Optional[Environment] = None) -> None:
        self._values: Dict[str, LoxObject] = dict()
        self.enclosing = enclosing

    def define(self, name: str, value: LoxObject) -> None:
        self._values[name] = value

    def assign(self, name: Token, value: LoxObject) -> None:
        if name.lexeme not in self._values:
            if self.enclosing:
                self.enclosing.assign(name, value)
                return
            raise LoxRuntimeError.at_token(name, f"Undefined variable '{name.lexeme}'.", fatal=True)
        self.define(name.lexeme, value)

    def get(self, name: Token) -> LoxObject:
        try:
            return self._values[name.lexeme]
        except KeyError:
            if self.enclosing:
                return self.enclosing.get(name)
            raise LoxRuntimeError.at_token(name, f"Undefined variable '{name.lexeme}'.", fatal=True)
