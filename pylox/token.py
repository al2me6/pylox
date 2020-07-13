from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterator, Optional

from pylox.lox_types import LoxLiteral


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
    QUESTION = "?"
    COLON = ":"
    # compoundable
    STAR = "*"
    BANG = "!"
    EQUAL = "="
    GREATER = ">"
    LESS = "<"
    STAR_STAR = "**"
    BANG_EQUAL = "!="
    EQUAL_EQUAL = "=="
    EQUAL_GREATER = "=>"
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
    SWITCH = "@SWITCH"
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
SINGLE_CHAR_TOKENS = tuple(filter(
    lambda val: isinstance(val, str) and len(val) == 1,
    Tk.iter_values()
))
COMPOUND_TOKENS = tuple(filter(
    lambda val: isinstance(val, str) and len(val) == 2,
    Tk.iter_values()
))


@dataclass
class Token:
    """A representation of a token. Note that offset is counted as the number of characters
    between the start of the source code and the end of the token's lexeme."""
    token_type: Tk
    lexeme: str
    literal: Optional[LoxLiteral]
    offset: int

    @classmethod
    def create_arbitrary(cls, token_type: Tk, lexeme: str, literal: Optional[LoxLiteral] = None) -> Token:
        return cls(token_type, lexeme, literal, -1)

    def __eq__(self, other: Any) -> bool:
        """Compare a `TokenType` to a `Token`'s own type.

        i.e., a `Token` of type `FOO` is equal to `TokenType.FOO`. This provides better
        ergonomics when used in a `StreamView`."""
        if isinstance(other, Tk):
            return self.token_type is other
        return super().__eq__(other)

    def __str__(self) -> str:
        attributes = ", ".join(
            f"{name}={repr(getattr(self, name))}"
            for name in ("lexeme", "literal")
            if hasattr(self, name)
        )
        return f"{self.token_type.name}{': ' if attributes else ''}{attributes}"

    def to_string(self) -> str:
        """Replicate `toString()` output from JLox."""
        attributes = f"{self.lexeme} {str(self.literal).replace('None', 'null')}"
        return f"{self.token_type.name} {attributes}"
