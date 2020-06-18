import sys
from enum import Flag, auto
from typing import Any

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


class Debug(Flag):
    DUMP_TOKENS = auto()
    DUMP_AST = auto()
    NO_PARSE = auto()
    NO_INTERPRET = auto()
    JAVA_STYLE_TOKENS = auto()


NOT_REACHED = AssertionError("Unreachable code reached")
