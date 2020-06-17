from __future__ import annotations

from enum import IntEnum, auto
from typing import Callable, Dict, List, NamedTuple, NoReturn, Optional, Set, Tuple

from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.expr import *
from pylox.stmt import *
from pylox.streamview import StreamView
from pylox.token import Token
from pylox.token import TokenType as TT
from pylox.utilities import NOT_REACHED, dump_internal


class Prec(IntEnum):
    NONE = auto()
    ASSIGNMENT = auto()
    OR = auto()
    AND = auto()
    EQUALITY = auto()
    COMPARISON = auto()
    TERM = auto()
    FACTOR = auto()
    UNARY = auto()
    CALL = auto()
    PRIMARY = auto()

    def as_right_assoc(self) -> Prec:
        return self.__class__(self.value - 1)


INFIX_OPERATION_PRECEDENCE = {
    TT.STAR: Prec.FACTOR,
    TT.SLASH: Prec.FACTOR,
    TT.PLUS: Prec.TERM,
    TT.MINUS: Prec.TERM,
    TT.GREATER: Prec.COMPARISON,
    TT.GREATER_EQUAL: Prec.COMPARISON,
    TT.LESS: Prec.COMPARISON,
    TT.LESS_EQUAL: Prec.COMPARISON,
    TT.EQUAL_EQUAL: Prec.EQUALITY,
    TT.BANG_EQUAL: Prec.EQUALITY,
    TT.EQUAL: Prec.ASSIGNMENT,
}


class Parser:
    """A simple Pratt parser.

    Its logic is derived from `clox`'s implementation, though the implementation is heavily inspired by Aleksey
    Kladov's article on the subject: https://matklad.github.io/2020/04/13/simple-but-powerful-pratt-parsing.html.
    """

    def __init__(
            self,
            tokens: List[Token],
            error_handler: LoxErrorHandler,
            *,
            dump: bool = False
    ) -> None:
        self._tv = StreamView(tokens)
        self._error_handler = error_handler
        self._dump = dump

    def parse(self) -> Expr:
        try:
            parsed_tree = self.parse_until_precedence(Prec.ASSIGNMENT)
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            raise NOT_REACHED
        else:
            if self._dump:
                dump_internal("AST", parsed_tree)
            return parsed_tree

    def parse_until_precedence(self, min_precedence: Prec) -> Expr:
        return self._expression(min_precedence)

    # ~~~ helper functions ~~~

    def _has_next(self) -> bool:
        if self._tv.has_next():
            if self._tv.peek() != TT.EOF:
                return True
        return False

    def _expect_next(self, expected: Set[TT], message: str) -> Token:
        if self._tv.match(*expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message, fatal=True)

    def _synchronize(self) -> None:
        self._tv.advance()
        while self._has_next():
            prev = self._tv.peek_unwrap(-1)
            if prev.token_type is TT.SEMICOLON:
                return
            if self._tv.match(TT.CLASS, TT.FUN, TT.VAR, TT.FOR, TT.IF, TT.WHILE, TT.PRINT, TT.RETURN):
                return
            self._tv.advance()
        return

    # ~~~ parsers ~~~

    def _expression(self, min_precedence: Prec) -> Expr:
        # Parse prefix operators.
        token = self._tv.advance()
        left: Expr
        if (token_type := token.token_type) is TT.LEFT_PAREN:
            enclosed = self._expression(Prec.ASSIGNMENT)
            self._expect_next({TT.RIGHT_PAREN}, "Expected ')' after expression.")
            left = GroupingExpr(enclosed)
        elif token_type in {TT.MINUS, TT.BANG}:
            left = UnaryExpr(token, self._expression(Prec.FACTOR))
        elif token_type in {TT. STRING, TT.NUMBER}:
            left = LiteralExpr(token.literal)
        else:
            raise LoxSyntaxError.at_token(token, "Expected expression.", fatal=True)

        # Lox does not have postfix operators.

        # Parse infix operators.
        while self._has_next():
            token = self._tv.advance()
            token_type = token.token_type
            if INFIX_OPERATION_PRECEDENCE[token_type] <= min_precedence:
                break
            if token_type in INFIX_OPERATION_PRECEDENCE:
                left = BinaryExpr(left, token, self._expression(INFIX_OPERATION_PRECEDENCE[token_type]))

        return left


__all__ = ("Parser",)
