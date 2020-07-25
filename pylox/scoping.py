from contextlib import contextmanager
from dataclasses import dataclass
from typing import TypeVar, Generic, List, Dict, Optional

from pylox.stmt import Stmt

K = TypeVar("K")
V = TypeVar("V")


class ScopeManager(Generic[K, V]):
    def __init__(self, base: Optional[Dict[K, V]] = None) -> None:
        self._stack: List[Dict[K, V]] = [{}]
        if base is not None:
            for key, val in base.items():
                self.define(key, val)

    @contextmanager
    def scope(self, *, dummy: bool = False):  # type: ignore
        if dummy:
            yield
        else:
            self._stack.append(dict())
            try:
                yield
            finally:
                self._stack.pop()

    @property
    def base(self) -> Dict[K, V]:
        return self._stack[0]

    def resolve(self, key: K) -> Optional[V]:
        for scope in reversed(self._stack):
            if (val := scope.get(key)) is not None:
                return val
        return None

    def define(self, key: K, value: V) -> None:
        self._stack[-1][key] = value

    def assign(self, key: K, value: V) -> bool:
        for scope in reversed(self._stack):
            if key in scope:
                scope[key] = value
                return True
        return False


@dataclass
class LoxScope:
    body: List[Stmt]
