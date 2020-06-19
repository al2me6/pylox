import sys
from enum import Flag, auto
from typing import Any, Iterator, Tuple

from pylox.token import Token


def dump_internal(name: str, *content: Any) -> None:
    """Output each item in `content` with a fancy header."""
    heading_length = 20
    print(f"{f'{name} Dump':~^{heading_length}}")  # Center and pad the title to HEADING_LENGTH characters long.
    print(*content, sep="\n")
    print("~"*heading_length)


def eprint(*args, **kwargs) -> None:
    """`print()` to stderr."""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


def lox_object_to_str(obj: Any) -> str:
    """Represent a Lox object as a string."""
    if obj is None:
        return "nil"  # The null type is "nil" in Lox.
    string = str(obj)
    if isinstance(obj, float) and string.endswith(".0"):
        string = string[:-2]  # Output 100.0 as 100, etc.
    elif isinstance(obj, bool):
        string = string.lower()  # Convert "True" to "true", etc.
    return string


class Debug(Flag):
    DUMP_TOKENS = auto()
    DUMP_AST = auto()
    NO_PARSE = auto()
    NO_INTERPRET = auto()
    JAVA_STYLE_TOKENS = auto()


def ast_node_pretty_printer(obj: Any, base_name: str) -> Tuple[str, Iterator[str]]:
    simplified_name = type(obj).__name__.replace(base_name, "").lower()
    attrs = (val.lexeme if isinstance(val, Token) else str(val) for val in obj.__dict__.values())
    return simplified_name, attrs


NOT_REACHED = AssertionError("Unreachable code reached")
