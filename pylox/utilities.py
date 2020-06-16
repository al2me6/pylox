import sys
from enum import Flag, auto
from typing import Any

HEADING_LENGTH = 20


def dump_internal(name: str, *content: Any) -> None:
    """Output each item in `content` with a fancy header."""
    print(f"{f'{name} Dump':~^{HEADING_LENGTH}}")  # Center and pad the title to HEADING_LENGTH characters long.
    print(*content, sep="\n")
    print("~"*HEADING_LENGTH)


def eprint(*args, **kwargs) -> None:
    """`print()` to stderr."""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


class Debug(Flag):
    DUMP_TOKENS = auto()
    DUMP_AST = auto()
    NO_PARSE = auto()
    NO_INTERPRET = auto()
    JAVA_STYLE_TOKENS = auto()


NOT_REACHED = AssertionError("Unreachable code reached")
