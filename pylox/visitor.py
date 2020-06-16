from __future__ import annotations  # Circular references in annotations.

from abc import ABC
from typing import Any


class Visitable(ABC):
    """Base class that accepts visitors in the visitor pattern."""

    def accept(self, visitor: Visitor) -> Any:
        return visitor.visit(self)


class Visitor(ABC):
    """Base class that acts as a visitor in the visitor pattern.

    Implementations of visit methods are structured as follows:
    `def _visit_<Class>__(self, visitable)`
    """

    def visit(self, visitable: Visitable) -> Any:
        """Attempt to find and call the correct visitor function."""
        visitable_name = type(visitable).__name__
        if impl := getattr(type(self), f"_visit_{visitable_name}__", None):
            return impl(self, visitable)
        raise NotImplementedError(f"{type(self).__name__} does not implement visit() for {visitable_name}")
