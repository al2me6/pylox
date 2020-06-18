from __future__ import annotations

from enum import IntEnum, auto
from typing import List, Set

from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.expr import *
from pylox.stmt import *
from pylox.streamview import StreamView
from pylox.token import Tk, Token
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
    EXP = auto()
    UNARY = auto()
    CALL = auto()
    PRIMARY = auto()

    def as_right_associative(self) -> Prec:
        return self.__class__(self.value - 1)


INFIX_OPERATION_PRECEDENCE = {
    Tk.STAR_STAR: Prec.EXP,
    Tk.STAR: Prec.FACTOR,
    Tk.SLASH: Prec.FACTOR,
    Tk.PLUS: Prec.TERM,
    Tk.MINUS: Prec.TERM,
    Tk.GREATER: Prec.COMPARISON,
    Tk.GREATER_EQUAL: Prec.COMPARISON,
    Tk.LESS: Prec.COMPARISON,
    Tk.LESS_EQUAL: Prec.COMPARISON,
    Tk.EQUAL_EQUAL: Prec.EQUALITY,
    Tk.BANG_EQUAL: Prec.EQUALITY,
    Tk.EQUAL: Prec.ASSIGNMENT,
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
            parsed_tree = self._parse_until_precedence(Prec.ASSIGNMENT)
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            raise NOT_REACHED
        else:
            if self._dump:
                dump_internal("AST", parsed_tree)
            return parsed_tree

    def _parse_until_precedence(self, min_precedence: Prec) -> Expr:
        return self._expression(min_precedence)

    # ~~~ helper functions ~~~

    def _has_next(self) -> bool:
        if self._tv.has_next():
            if self._tv.peek() != Tk.EOF:
                return True
        return False

    def _expect_next(self, expected: Set[Tk], message: str) -> Token:
        if self._tv.match(*expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message, fatal=True)

    def _synchronize(self) -> None:
        self._tv.advance()
        while self._has_next():
            prev = self._tv.peek_unwrap(-1)
            if prev.token_type is Tk.SEMICOLON:
                return
            if self._tv.match(Tk.CLASS, Tk.FUN, Tk.VAR, Tk.FOR, Tk.IF, Tk.WHILE, Tk.PRINT, Tk.RETURN):
                return
            self._tv.advance()
        return

    # ~~~ parsers ~~~

    def _expression(self, min_precedence: Prec) -> Expr:
        # Parse prefix operators and literals.
        token = self._tv.advance()
        left: Expr
        if (token_type := token.token_type) is Tk.LEFT_PAREN:
            enclosed = self._expression(Prec.ASSIGNMENT)
            self._expect_next({Tk.RIGHT_PAREN}, "Expected ')' after expression.")
            left = GroupingExpr(enclosed)
        elif token_type in {Tk.BANG, Tk.MINUS}:
            left = UnaryExpr(token, self._expression(Prec.FACTOR))
        elif token_type in {Tk.FALSE, Tk.TRUE, Tk.NIL, Tk.NUMBER, Tk.STRING}:
            left = LiteralExpr({Tk.FALSE: False, Tk.TRUE: True, Tk.NIL: None}.get(token_type, token.literal))
        else:
            raise LoxSyntaxError.at_token(token, "Expected expression.", fatal=True)

        # Parse the "right hand side".
        while self._has_next():
            token = self._tv.peek_unwrap()
            token_type = token.token_type
            # Parse infix operators.
            if (prec := INFIX_OPERATION_PRECEDENCE.get(token_type)):  # Check if the operator is valid.
                # Check if it has high enough precedence for its expression to be parsed as an
                # operand of the "parent" half-parsed expression.
                if prec <= min_precedence:
                    break
                # If so, consume and parse it.
                self._tv.advance()
                right = self._expression(prec)
                left = BinaryExpr(token, left, right)
            else:  # If it's not an operator, we're done.
                break

        return left


__all__ = ("Parser",)
