from __future__ import annotations

from typing import Any, Dict, Optional

from pylox.error import LoxRuntimeError
from pylox.token import Token


class Environment:
    def __init__(self, enclosing: Optional[Environment] = None) -> None:
        self._values: Dict[str, Any] = dict()
        self.enclosing = enclosing

    def define(self, name: str, value: Any) -> None:
        self._values[name] = value

    def assign(self, name: Token, value: Any) -> None:
        if name.lexeme not in self._values:
            if self.enclosing:
                self.enclosing.assign(name, value)
                return
            raise LoxRuntimeError.at_token(name, "Undefined variable.", fatal=True)
        self.define(name.lexeme, value)

    def get(self, name: Token) -> Any:
        try:
            return self._values[name.lexeme]
        except KeyError:
            if self.enclosing:
                return self.enclosing.get(name)
            raise LoxRuntimeError.at_token(name, "Undefined variable.", fatal=True)
