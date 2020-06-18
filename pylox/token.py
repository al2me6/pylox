from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterator, Optional, Union


class Tk(Enum):
    # single-char
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    COMMA = ","
    DOT = "."
    MINUS = "-"
    PLUS = "+"
    SEMICOLON = ";"
    STAR = "*"
    # compoundable
    BANG = "!"
    EQUAL = "="
    GREATER = ">"
    LESS = "<"
    BANG_EQUAL = "!="
    EQUAL_EQUAL = "=="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    SLASH = auto()
    # keywords
    AND = "@AND"
    CLASS = "@CLASS"
    ELSE = "@ELSE"
    FALSE = "@FALSE"
    FUN = "@FUN"
    FOR = "@FOR"
    IF = "@IF"
    NIL = "@NIL"
    OR = "@OR"
    PRINT = "@PRINT"
    RETURN = "@RETURN"
    SUPER = "@SUPER"
    THIS = "@THIS"
    TRUE = "@TRUE"
    VAR = "@VAR"
    WHILE = "@WHILE"
    # literals
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    EOF = auto()

    @classmethod
    def iter_values(cls) -> Iterator[Any]:
        """Iterate over the values of the enum."""
        for variant in cls:
            yield variant.value


# auto() variants have integer values. Filter the remaining values by length to isolate the target ones.
# THIS IS FRAGILE CODE: addition single-character keywords or three-character symbols will break this.
SINGLE_CHAR_TOKENS = tuple(filter(lambda val: isinstance(val, str) and len(val) == 1, Tk.iter_values()))
COMPOUND_TOKENS = tuple(filter(lambda val: isinstance(val, str) and len(val) == 2, Tk.iter_values()))


LiteralValue = Union[str, float]


@dataclass
class Token:
    """A representation of a token. Note that offset is counted as the number of characters
    between the start of the source code and the end of the token's lexeme."""
    token_type: Tk
    lexeme: str
    literal: Optional[LiteralValue]
    offset: int

    def __eq__(self, other: Any) -> bool:
        """Compare a `TokenType` to a `Token`'s own type.

        i.e., a `Token` of type `FOO` is equal to `TokenType.FOO`. This provides better
        ergonomics when used with `StreamView`, given the use-case of Token."""
        if isinstance(other, Tk):
            return self.token_type is other
        return super().__eq__(other)

    def __str__(self) -> str:
        attributes = ", ".join(
            f"{name}={repr(getattr(self, name))}"
            for name in ("lexeme", "literal")
            if getattr(self, name)
        )
        return f"{self.token_type.name}{': ' if attributes else ''}{attributes}"

    def to_string(self) -> str:
        """Replicate `toString()` output from JLox."""
        attributes = f"{self.lexeme} {str(self.literal).replace('None', 'null')}"
        return f"{self.token_type.name} {attributes}"


__all__ = ("SINGLE_CHAR_TOKENS", "COMPOUND_TOKENS", "Token", "Tk", "LiteralValue",)
