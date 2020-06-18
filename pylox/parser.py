from enum import IntEnum, auto
from typing import List, Optional, Set

from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.expr import *
from pylox.stmt import *
from pylox.streamview import StreamView
from pylox.token import Tk, Token
from pylox.utilities import dump_internal


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


INFIX_OPERATOR_PRECEDENCE = {
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

RIGHT_ASSOCIATIVE_OPERATORS = {
    Tk.STAR_STAR,
    Tk.EQUAL,
}


def _get_infix_operator_precedence_by_associativity(op: Tk, prec: Prec) -> Prec:
    if op in RIGHT_ASSOCIATIVE_OPERATORS:
        return Prec(prec.value - 1)
    return prec


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
        self._statements: List[Stmt] = list()

    def parse(self) -> List[Stmt]:
        while self._has_next():
            if (declaration := self._declaration()):
                self._statements.append(declaration)
        if self._dump:
            dump_internal("AST", *self._statements)
        return self._statements

    # ~~~
    # helper functions ~~~

    def _has_next(self) -> bool:
        if self._tv.has_next():
            if self._tv.peek() != Tk.EOF:
                return True
        return False

    def _expect_next(self, expected: Set[Tk], message: str) -> Token:
        if self._tv.match(*expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message)

    def _expect_semicolon(self) -> None:
        self._expect_next({Tk.SEMICOLON}, "Expected ';' after expression.")

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

    # ~~~ Parsers ~~~

    def _declaration(self) -> Optional[Stmt]:
        decl: Optional[Stmt]
        try:
            if self._tv.advance_if_match(Tk.VAR):
                decl = self._variable_declaration_parselet()
            else:
                decl = self._statement()
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            self._synchronize()
            decl = None

        return decl

    def _variable_declaration_parselet(self) -> VarStmt:
        name = self._expect_next({Tk.IDENTIFIER}, "Expected variable name.")
        expr: Optional[Expr] = None
        if self._tv.advance_if_match(Tk.EQUAL):
            expr = self._expression()
        self._expect_semicolon()
        return VarStmt(name, expr)

    def _statement(self) -> Stmt:
        stmt: Stmt
        if self._tv.advance_if_match(Tk.PRINT):
            stmt = PrintStmt(self._expression())
            self._expect_semicolon()
        elif self._tv.advance_if_match(Tk.LEFT_BRACE):
            stmt = self._block_statement_parselet()
        else:
            stmt = ExpressionStmt(self._expression())
            self._expect_semicolon()
        return stmt

    def _block_statement_parselet(self) -> BlockStmt:
        stmts: List[Stmt] = list()
        while self._has_next():
            if self._tv.peek_unwrap().token_type is Tk.RIGHT_BRACE:
                break
            if (stmt := self._declaration()):
                stmts.append(stmt)
        self._expect_next({Tk.RIGHT_BRACE}, "Expected '}' after block.")
        return BlockStmt(stmts)

    def _expression(self, min_precedence: Prec = Prec.NONE) -> Expr:
        # Parse prefix operators and literals.
        token = self._tv.advance()
        left: Expr
        if (token_type := token.token_type) is Tk.LEFT_PAREN:
            enclosed = self._expression()
            self._expect_next({Tk.RIGHT_PAREN}, "Expected ')' after expression.")
            left = GroupingExpr(enclosed)
        elif token_type in {Tk.BANG, Tk.MINUS}:
            left = UnaryExpr(token, self._expression(Prec.FACTOR))
        elif token_type in {Tk.FALSE, Tk.TRUE, Tk.NIL, Tk.NUMBER, Tk.STRING}:
            left = LiteralExpr({Tk.FALSE: False, Tk.TRUE: True, Tk.NIL: None}.get(token_type, token.literal))
        elif token_type is Tk.IDENTIFIER:
            left = VariableExpr(token)
        else:
            raise LoxSyntaxError.at_token(token, "Expected expression.")

        # Parse the "right hand side".
        while self._has_next():
            op = self._tv.peek_unwrap()
            op_type = op.token_type
            # Parse infix operators.
            if (prec := INFIX_OPERATOR_PRECEDENCE.get(op_type)):  # Check if the operator is valid.
                # Check if it has high enough precedence for its expression to be parsed as an
                # operand of the "parent" half-parsed expression.
                if prec <= min_precedence:
                    break
                # Consume the operator and parse the RHS with the appropriate associativity.
                self._tv.advance()
                right = self._expression(_get_infix_operator_precedence_by_associativity(op_type, prec))
                if op_type is Tk.EQUAL:
                    left = self._assignment_expression_parselet(op, left, right)
                else:
                    left = BinaryExpr(op, left, right)
            else:  # If it's not an operator, we're done.
                break

        return left

    def _assignment_expression_parselet(self, op: Token, left: Expr, right: Expr) -> AssignmentExpr:
        if isinstance(left, VariableExpr):
            return AssignmentExpr(left.name, right)
        raise LoxSyntaxError.at_token(op, "Invalid assignment target.")


__all__ = ("Parser",)
