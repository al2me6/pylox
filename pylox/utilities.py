import sys
from typing import Any

HEADING_LENGTH = 20


def dump_internal(name: str, *content: Any) -> None:
    print(f"{f'{name} Dump':~^{HEADING_LENGTH}}")
    print(*content, sep="\n")
    print("~"*HEADING_LENGTH)


def eprint(*args, **kwargs) -> None:
    """`print()` to stderr"""
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


NOT_REACHED = False
