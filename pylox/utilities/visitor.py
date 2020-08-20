from __future__ import annotations  # Circular references in annotations.

from abc import ABC
from typing import Callable, Generic, Optional, TypeVar

V = TypeVar("V")
R = TypeVar("R")


class Visitor(Generic[V, R], ABC):
    """Base class that acts as a visitor in the visitor pattern.

    Implementations of visit methods are structured as follows:
    `def _visit_<Class>__(self, visitable)`
    """

    def visit(self, visitable: V) -> R:
        """Attempt to find and call the correct visitor function."""
        for class_ in (type(visitable), *type(visitable).mro()):
            impl: Optional[Callable[[Visitor[V, R], V], R]] = getattr(type(self), f"_visit_{class_.__name__}__", None)
            if impl is not None:
                return impl(self, visitable)
        raise NotImplementedError(f"{type(self).__name__} does not implement visit() for {type(visitable).__name__}")
