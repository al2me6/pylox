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
    TERNARY = auto()
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
    Tk.QUESTION: Prec.TERNARY,
    Tk.EQUAL: Prec.ASSIGNMENT,
}

RIGHT_ASSOCIATIVE_OPERATORS = {
    Tk.STAR_STAR,
    Tk.EQUAL,
    Tk.QUESTION,
}


def _adjust_precedence_for_operator_associativity(prec: Prec, op: Tk) -> Prec:
    if op in RIGHT_ASSOCIATIVE_OPERATORS:
        return Prec(prec.value - 1)
    return prec


class Parser:
    """A simple Pratt parser.

    Its logic is derived from `clox`'s implementation, though the implementation
    is motivated by Aleksey Kladov's article on the subject:
    https://matklad.github.io/2020/04/13/simple-but-powerful-pratt-parsing.html.
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
        if self._dump and not self._error_handler.error_state:
            dump_internal("AST", *self._statements)
        return self._statements

    # ~~~ Helper functions ~~~

    def _has_next(self) -> bool:
        if self._tv.has_next():
            if self._tv.peek_unwrap().token_type is not Tk.EOF:
                return True
        return False

    def _expect_next(self, expected: Set[Tk], message: str) -> Token:
        if self._tv.match(*expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message)

    def _expect_semicolon(self) -> None:
        self._expect_next({Tk.SEMICOLON}, "Expect ';' after expression.")

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
        name = self._expect_next({Tk.IDENTIFIER}, "Expect variable name.")
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
        self._expect_next({Tk.RIGHT_BRACE}, "Expect '}' after block.")
        return BlockStmt(stmts)

    def _expression(self, min_precedence: Prec = Prec.NONE) -> Expr:
        """The core of the Pratt parser.

            Ex. parsing "a / b ** c ** d + -e"
            > Parsed (a).
            > Next operator is /, stronger than NONE -> grab (a), parse the RHS expr until FACTOR.
              > Parsed (b).
              > Next operator is **, stronger than FACTOR -> grab (b), parse the RHS until EXP...
                But! ** is right associative, so the actual Prec passed is one less: FACTOR.
                > Parsed (c).
                > Next operator is **, which is not strong enough compared to EXP, but *is* compared
                  to FACTOR -> parse RHS until (EXP - 1). In effect, lowering the min Prec in the
                  previous pass allows the same operator, if it appears again, to grab the LHS.
                  > Parsed (d).
                  > Next operator is +, weaker than Prec of preceding ** -> unwind.
                > Received (d) as the RHS for **.
                > Parsed (** c d) as the new LHS.
                > Next operator is +, weaker than ** -> unwind.
              > Received (** c d) as RHS.
              > Parsed (** b (** c d)) as LHS.
              > Next operator is again +, weaker than / -> unwind.
            > Received (** b (** c d)) as RHS.
            > Parsed (/ a (** b (** c d))) as LHS.
            > There are more tokens -> loop over.
            > Next operator is +, stronger than NONE -> parse RHS until TERM.
              > Parsed (-) -> parse RHS at lowest Prec: NONE.
              > Parsed (- e) as LHS.
              > No more tokens -> unwind.
            > Received (- e) as RHS.
            > Parsed (+ (/ a (** b (** c d))) (- e)) as LHS.
            > No more tokens -> unwind.
            > Complete.
        """
        # Parse prefix operators and literals into the LHS.
        token = self._tv.advance()
        left: Expr
        if (token_type := token.token_type) is Tk.LEFT_PAREN:
            enclosed = self._expression()
            self._expect_next({Tk.RIGHT_PAREN}, "Expect ')' after expression.")
            left = GroupingExpr(enclosed)
        elif token_type in {Tk.BANG, Tk.MINUS}:
            left = UnaryExpr(token, self._expression(Prec.UNARY))
        elif token_type in {Tk.FALSE, Tk.TRUE, Tk.NIL, Tk.NUMBER, Tk.STRING}:
            left = LiteralExpr({
                Tk.FALSE: False,
                Tk.TRUE: True,
                Tk.NIL: None
            }.get(token_type, token.literal))
        elif token_type is Tk.IDENTIFIER:
            left = VariableExpr(token)
        else:
            raise LoxSyntaxError.at_token(token, "Expect expression.")

        # Parse the operator and the RHS, if possible.
        while self._has_next():
            op = self._tv.peek_unwrap()
            op_type = op.token_type

            # Parse infix operators.
            if (prec := INFIX_OPERATOR_PRECEDENCE.get(op_type)):  # Check if the operator is valid.
                # Check if the operator has high enough relative precedence for the parsed LHS to be
                # bound to itself. If not, then we break out of this pass and return so that the LHS
                # becomes the RHS of a previously half-parsed, higher-precedence operation.
                if prec <= min_precedence:
                    break

                # Consume the operator.
                self._tv.advance()

                # Parse the "middle" of the ternary if operator. Since it is enclosed within the
                # operator (between ? and :), parse the entirety of the expression.
                if op_type is Tk.QUESTION:
                    middle = self._expression()
                    self._expect_next({Tk.COLON}, "Expect ':' in ternary if operator.")

                # Parse the RHS up to the current operator's precedence, taking associativity into account.
                right = self._expression(_adjust_precedence_for_operator_associativity(prec, op_type))

                # Build the new LHS.
                if op_type is Tk.QUESTION:
                    left = TernaryIfExpr(left, middle, right)
                elif op_type is Tk.EQUAL:
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
