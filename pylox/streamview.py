from __future__ import annotations  # Reference the parent class in methods' annotations.

from typing import Any, Generic, Iterator, Optional, Sequence, TypeVar, overload

T = TypeVar("T")  # pylint: disable=invalid-name


class StreamView(Generic[T]):
    """A "scrolling" view of a Sequence, similar to an Iterator. StreamView allows peeking
    of arbitrary elements without consumption and retrieval of arbitrary ranges."""
    # pylint: disable=multiple-statements

    def __init__(self, sequence: Sequence[T]) -> None:
        self.sequence = sequence
        self.current_index: int = 0
        self.marker_index: Optional[int] = None

    @overload
    def __getitem__(self, index: int) -> T: pass

    @overload
    def __getitem__(self: StreamView[str], index: slice) -> str: pass

    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: pass

    def __getitem__(self, index):
        return self.sequence[index]

    def __len__(self) -> int:
        return len(self.sequence)

    def __iter__(self) -> Iterator[T]:
        return iter(self.sequence)

    def _fallthrough(self, index: Optional[int]) -> int:
        """Use the value of a predefined index if the passed index is None."""
        if index is not None:
            return index
        return self.current_index

    def has_next(self, index: Optional[int] = None) -> bool:
        return self._fallthrough(index) < len(self)

    def set_marker(self, index: Optional[int] = None) -> None:
        """Place a marker at the current (or a specified) index,
        for use by `get_slice_from_marker()`."""
        self.marker_index = self._fallthrough(index)

    def unset_marker(self) -> None:
        self.marker_index = None

    def peek(self, lookahead: int = 0) -> Optional[T]:
        """Return the value `lookahead` from the next one, if there is one."""
        index = self.current_index + lookahead
        if self.has_next(index):
            return self[index]
        return None

    def peek_unwrap(self, lookahead: int = 0) -> T:
        """Variant of `peek()` that always returns a value. Produces an exception
        if there is not a value at `lookahead`."""
        res = self.peek(lookahead)
        assert res is not None
        return res

    def match(self, *expected: Any) -> bool:
        """Test if the next value is one of the `expected` values."""
        if self.peek() in expected:
            return True
        return False

    def advance(self) -> T:
        """Consume the next value if there is one and return it."""
        if (next_item := self.peek()) is not None:
            self.current_index += 1
            return next_item
        raise IndexError("Items have been exhausted.")

    def advance_if_match(self, *expected: Any) -> bool:
        """Test if the next value is one of the `expected` values. If so, consume it."""
        if self.match(*expected):
            self.advance()
            return True
        return False

    @overload
    def get_slice_from_marker(self: StreamView[str]) -> str: pass

    @overload
    def get_slice_from_marker(self) -> Sequence[T]: pass

    def get_slice_from_marker(self):
        """Return the slice from the marked position to the current value."""
        if self.marker_index is not None:
            return self[self.marker_index:self.current_index]
        raise RuntimeError("Marker is not set.")
