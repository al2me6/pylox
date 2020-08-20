from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Generic, Iterator, List, TypeVar

K = TypeVar("K")
V = TypeVar("V")

Frame = Dict[K, V]
RawStack = List[Frame[K, V]]


class StackedMap(Generic[K, V]):
    def __init__(self) -> None:
        self._stack: RawStack[K, V] = [{}]

    def __getitem__(self, idx):  # type: ignore
        return self._stack[idx]

    def clear(self) -> None:
        self._stack.clear()
        self._stack.append({})

    @contextmanager
    def scope(self) -> Iterator[None]:
        self._stack.append(dict())
        try:
            yield
        finally:
            self._stack.pop()

    @contextmanager
    def graft(self, tail: RawStack[K, V]) -> Iterator[None]:
        original_tail = self.tail()
        self._stack = [self._stack[0], *tail]
        try:
            yield
        finally:
            self._stack = [self._stack[0], *original_tail]

    def tail(self) -> RawStack[K, V]:
        return self._stack[1:]

    def is_local(self) -> bool:
        return len(self._stack) > 1

    def define(self, key: K, value: V) -> None:
        self._stack[-1][key] = value

    def assign(self, key: K, value: V) -> None:
        for frame in reversed(self._stack):
            if key in frame:
                frame[key] = value
                return
        raise KeyError

    def get(self, key: K) -> V:
        for frame in reversed(self._stack):
            try:
                return frame[key]
            except KeyError:
                pass
        raise KeyError
