from contextlib import contextmanager
from typing import Generic, Iterator, List, TypeVar

T = TypeVar("T")


class ScopedStateHandler(Generic[T]):
    def __init__(self, default: T) -> None:
        self._state: List[T] = [default]

    @contextmanager
    def enter(self, state: T) -> Iterator[None]:
        self._state.append(state)
        try:
            yield
        finally:
            self._state.pop()

    @property
    def state(self) -> T:
        return self._state[-1]
