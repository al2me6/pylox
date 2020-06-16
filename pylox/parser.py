from typing import List, Optional, Set

# pylint: disable=unused-wildcard-import  # Somehow it decides to import the file's own import statements?
from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.expr import *
from pylox.stmt import *
from pylox.streamview import StreamView
from pylox.token import Token
from pylox.token import TokenType as TT
from pylox.utilities import dump_internal


class Parser:
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

    def parse(self) -> Optional[Expr]:
        try:
            parsed_tree = self._expression()
            self._expect_next({TT.EOF}, "Expected end of statement")
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            return None
        else:
            if self._dump:
                dump_internal("AST", parsed_tree)
            return parsed_tree

    # ~~~ Helper functions ~~~

    def _expect_next(self, expected: Set[TT], message: str) -> Token:
        if self._tv.match(*expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message)

    def _synchronize(self) -> None:
        self._tv.advance()
        while self._tv.has_next():
            prev = self._tv.peek_unwrap(-1)
            if prev.token_type is TT.SEMICOLON:
                return
            if self._tv.match(TT.CLASS, TT.FUN, TT.VAR, TT.FOR, TT.IF, TT.WHILE, TT.PRINT, TT.RETURN):
                return
            self._tv.advance()
        return

    # ~~~ Expression parsers ~~~

    def _expression(self) -> Expr:
        return self._equality()

    def _equality(self) -> Expr:
        expr = self._comparison()

        while self._tv.advance_if_match(TT.BANG_EQUAL, TT.EQUAL_EQUAL):
            operator = self._tv.peek_unwrap(-1)
            right = self._comparison()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _comparison(self) -> Expr:
        expr = self._addition()

        while self._tv.advance_if_match(TT.GREATER, TT.GREATER_EQUAL, TT.LESS, TT.LESS_EQUAL):
            operator = self._tv.peek_unwrap(-1)
            right = self._addition()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _addition(self) -> Expr:
        expr = self._multiplication()

        while self._tv.advance_if_match(TT.MINUS, TT.PLUS):
            operator = self._tv.peek_unwrap(-1)
            right = self._multiplication()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _multiplication(self) -> Expr:
        expr = self._unary()

        while self._tv.advance_if_match(TT.SLASH, TT.STAR):
            operator = self._tv.peek_unwrap(-1)
            right = self._unary()
            expr = BinaryExpr(expr, operator, right)

        return expr

    def _unary(self) -> Expr:
        if self._tv.advance_if_match(TT.BANG, TT.MINUS):
            operator = self._tv.peek_unwrap(-1)
            right = self._unary()
            return UnaryExpr(operator, right)

        return self._primary()

    def _primary(self) -> Expr:
        try:
            literal = {
                TT.FALSE: lambda: False,
                TT.TRUE: lambda: True,
                TT.NIL: lambda: None,
                TT.NUMBER: lambda: self._tv.peek_unwrap().literal,
                TT.STRING: lambda: self._tv.peek_unwrap().literal,
            }[self._tv.peek().token_type]()  # type: ignore  # peek() -> None covered by except AttributeError.
        except (KeyError, AttributeError):
            pass
        else:
            self._tv.advance()
            return LiteralExpr(literal)

        if self._tv.advance_if_match(TT.LEFT_PAREN):
            expr = self._expression()
            self._expect_next({TT.RIGHT_PAREN}, "Expected ')' after expression")
            return GroupingExpr(expr)

        raise LoxSyntaxError(self._tv.peek_unwrap().offset, "Expected expression")
