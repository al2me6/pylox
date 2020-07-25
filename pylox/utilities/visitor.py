from __future__ import annotations  # Circular references in annotations.

from abc import ABC
from typing import Any


class Visitable(ABC):
    """Base class that accepts visitors in the visitor pattern."""

    def accept(self, visitor: Visitor, *args: Any, **kwargs: Any) -> Any:
        return visitor.visit(self, *args, **kwargs)


class Visitor(ABC):
    """Base class that acts as a visitor in the visitor pattern.

    Implementations of visit methods are structured as follows:
    `def _visit_<Class>__(self, visitable)`
    """

    def visit(self, visitable: Visitable, *args: Any, **kwargs: Any) -> Any:
        """Attempt to find and call the correct visitor function."""
        for class_ in (type(visitable), *type(visitable).mro()):
            if impl := getattr(type(self), f"_visit_{class_.__name__}__", None):
                return impl(self, visitable, *args, **kwargs)
        raise NotImplementedError(f"{type(self).__name__} does not implement visit() for {type(visitable).__name__}")
