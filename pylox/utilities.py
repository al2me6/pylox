import sys
from enum import Flag, auto
from typing import Any, Iterator, Optional, Set, Tuple, Type

from pylox.token import Token


class Debug(Flag):
    DUMP_TOKENS = auto()
    DUMP_AST = auto()
    NO_PARSE = auto()
    NO_INTERPRET = auto()
    JAVA_STYLE_TOKENS = auto()
    REDUCED_ERROR_REPORTING = auto()


def dump_internal(name: str, *content: Any) -> None:
    """Output each item in `content` with a fancy header."""
    heading_length = 20
    print(f"{name} Dump".center(heading_length, "~"))
    print(*content, sep="\n")
    print("~"*heading_length)


def eprint(*args, **kwargs) -> None:
    """`print()` to stderr."""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


def ast_node_pretty_printer(obj: Any, base_name: str) -> Tuple[str, Iterator[str]]:
    simplified_name = type(obj).__name__.replace(base_name, "").lower()
    attrs = (
        val.lexeme if isinstance(val, Token) else str(val)
        for val in vars(obj).values()
    )
    return simplified_name, attrs


def is_arabic_numeral(char: Optional[str]) -> bool:
    if char is None:
        return False
    return char in "1234567890"


def are_of_expected_type(expected_types: Set[Type[Any]], *obj: Any) -> bool:
    """Check if the `obj`s passed are all of one of the expected types."""
    for expected_type in expected_types:
        if all(isinstance(o, expected_type) for o in obj):
            return True
    return False


NOT_REACHED = AssertionError("Unreachable code reached")
