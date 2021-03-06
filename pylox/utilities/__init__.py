from typing import Any, Iterator, Optional, Set, Tuple, Type

from pylox.lexing.token import Token


def dump_internal(name: str, *content: Any) -> None:
    """Output each item in `content` with a fancy header."""
    heading_length = 20
    print(f"{name} Dump".center(heading_length, "~"))
    print(*content, sep="\n")
    print("~" * heading_length)


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
    return any(all(isinstance(o, exp_ty) for o in obj) for exp_ty in expected_types)


def indent(*block: str) -> str:
    return "".join(f"\t{line}\n" for blk in block for line in str(blk).splitlines())
