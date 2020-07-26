from __future__ import annotations

from enum import IntEnum, auto
from typing import Callable, Iterator, List, Optional, TypeVar, Union

from pylox.lexing.token import Tk, Token
from pylox.parsing.expr import *
from pylox.parsing.stmt import *
from pylox.language.lox_types import LoxIdentifier
from pylox.language.scoping import ScopeManager
from pylox.utilities import dump_internal
from pylox.utilities.error import LoxErrorHandler, LoxSyntaxError
from pylox.utilities.stream_view import StreamView

RIGHT_ASSOCIATIVE_OPERATORS = {
    Tk.STAR_STAR,
    Tk.EQUAL,
    Tk.QUESTION,
}


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

    def adjust_for_operator_associativity(self, op: Tk) -> Prec:
        if op in RIGHT_ASSOCIATIVE_OPERATORS:
            return self.__class__(self.value - 1)
        return self


OPERATOR_PRECEDENCE = {
    Tk.LEFT_PAREN: Prec.CALL,
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
    Tk.AND: Prec.AND,
    Tk.OR: Prec.OR,
    Tk.QUESTION: Prec.TERNARY,
    Tk.EQUAL: Prec.ASSIGNMENT,
}


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
        self._scopes: ScopeManager[str, LoxIdentifier] = ScopeManager()

    def parse(self) -> List[Stmt]:
        while self._has_next():
            if declaration := self._declaration():
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

    def _expect_next(self, expected: Tk, message: str) -> Token:
        if self._tv.match(expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message)

    def _expect_punct(self, symbol: Tk, message: str) -> None:
        self._expect_next(symbol, f"Expect '{symbol.value}' {message}.")

    def _synchronize(self) -> None:
        if not self._tv.has_next():
            return
        self._tv.advance()
        while self._has_next():
            if self._tv.peek_unwrap(-1).token_type is Tk.SEMICOLON:
                return
            if self._tv.match(Tk.CLASS, Tk.FUN, Tk.VAR, Tk.FOR, Tk.IF, Tk.WHILE, Tk.PRINT, Tk.RETURN):
                return
            self._tv.advance()
        return

    T = TypeVar("T")

    def _parse_repeatedly(
            self, parselet: Callable[[], Union[T, Optional[T]]],
            *,
            separator: Optional[Tk] = Tk.COMMA,
            terminator: Tk = Tk.RIGHT_PAREN,
            terminator_expect_message: str = "after expression"
    ) -> Iterator[T]:
        while self._has_next():
            if self._tv.peek_unwrap().token_type is terminator:
                break
            if result := parselet():
                yield result
            if separator:
                if not self._tv.advance_if_match(separator):
                    break
        self._expect_next(terminator, f"Expected '{terminator.value}' {terminator_expect_message}.")

    def _define_ident(self, ident: Token) -> LoxIdentifier:
        mangled_ident = LoxIdentifier(id(ident) ^ id(self))  # TODO: find some better scheme?
        self._scopes.define(ident.lexeme, mangled_ident)
        return mangled_ident

    def _resolve_ident(self, ident: Token) -> Optional[LoxIdentifier]:
        assert ident.token_type is Tk.IDENTIFIER
        return self._scopes.resolve(ident.lexeme)

    # ~~~ Parsers ~~~

    def _declaration(self) -> Optional[Stmt]:
        decl: Optional[Stmt]
        try:
            if self._tv.advance_if_match(Tk.VAR):
                decl = self._variable_declaration_parselet()
            elif self._tv.advance_if_match(Tk.FUN):
                decl = self._callable_object_parselet(kind="function")
            else:
                decl = self._statement()
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            self._synchronize()
            decl = None

        return decl

    def _callable_object_parselet(self, *, kind: str) -> FunctionStmt:
        name = self._expect_next(Tk.IDENTIFIER, f"Expect {kind} name.")
        self._define_ident(name)
        self._expect_punct(Tk.LEFT_PAREN, f"after {kind} name")
        with self._scopes.scope():
            params = list(self._parse_repeatedly(
                lambda: self._expect_next(Tk.IDENTIFIER, "Expect parameter name."),
                terminator_expect_message="after parameters"
            ))
            self._expect_punct(Tk.LEFT_BRACE, f"before {kind} body")
            body = self._block_statement_parselet()
        return FunctionStmt(name, params, body)

    def _variable_declaration_parselet(self) -> VarStmt:
        name = self._expect_next(Tk.IDENTIFIER, "Expect variable name.")
        mangled_ident = self._define_ident(name)
        expr = self._expression() if self._tv.advance_if_match(Tk.EQUAL) else None
        self._expect_punct(Tk.SEMICOLON, "after expression")
        return VarStmt(name, mangled_ident, expr)

    def _statement(self, *, unscoped_block: bool = False) -> Stmt:
        stmt: Stmt
        if self._tv.advance_if_match(Tk.FOR):
            stmt = self._for_statement_parselet()
        elif self._tv.advance_if_match(Tk.IF):
            stmt = self._if_statement_parselet()
        elif self._tv.advance_if_match(Tk.LEFT_BRACE):
            stmt = self._block_statement_parselet(unscoped=unscoped_block)
        elif self._tv.advance_if_match(Tk.SWITCH):
            stmt = self._switch_statement_parselet()
        elif self._tv.advance_if_match(Tk.PRINT):
            stmt = PrintStmt(self._expression())
            self._expect_punct(Tk.SEMICOLON, "after expression")
        elif self._tv.advance_if_match(Tk.RETURN):
            stmt = self._return_statement_parselet()
        elif self._tv.advance_if_match(Tk.WHILE):
            stmt = self._while_statement_parselet()
        else:
            stmt = self._expression_statement_parselet()
        return stmt

    def _block_statement_parselet(self, *, unscoped: bool = False) -> BlockStmt:
        with self._scopes.scope(dummy=unscoped):
            stmts = self._parse_repeatedly(
                self._declaration,
                separator=None,
                terminator=Tk.RIGHT_BRACE,
                terminator_expect_message="after block"
            )
        return BlockStmt(list(stmts))

    def _expression_statement_parselet(self) -> ExpressionStmt:
        stmt = ExpressionStmt(self._expression())
        self._expect_punct(Tk.SEMICOLON, "after expression")
        return stmt

    def _for_statement_parselet(self) -> Stmt:
        self._expect_punct(Tk.LEFT_PAREN, "after 'for'")

        with self._scopes.scope():
            initializer: Optional[Stmt]
            if self._tv.advance_if_match(Tk.SEMICOLON):
                initializer = None
            elif self._tv.advance_if_match(Tk.VAR):
                initializer = self._variable_declaration_parselet()
            else:
                initializer = self._expression_statement_parselet()

            condition = self._expression() if self._tv.peek() != Tk.SEMICOLON else LiteralExpr(True)
            self._expect_punct(Tk.SEMICOLON, "after loop condition")

            increment = self._expression() if self._tv.peek() != Tk.RIGHT_PAREN else None
            self._expect_punct(Tk.RIGHT_PAREN, "after for clauses")

            with self._scopes.scope():
                body = self._statement(unscoped_block=True)  # Already explicitly scoped - don't double-scope.

        if increment:
            body = BlockStmt([body, ExpressionStmt(increment)])
        body = WhileStmt(condition, body)
        if initializer:
            body = BlockStmt([initializer, body])

        return body

    def _if_statement_parselet(self) -> IfStmt:
        self._expect_punct(Tk.LEFT_PAREN, "after 'if'")
        condition = self._expression()
        self._expect_punct(Tk.RIGHT_PAREN, "after if condition")
        then_branch = self._statement()
        else_branch = self._statement() if self._tv.advance_if_match(Tk.ELSE) else None
        return IfStmt(condition, then_branch, else_branch)

    def _switch_statement_parselet(self) -> BlockStmt:
        self._expect_punct(Tk.LEFT_PAREN, "after 'switch'")
        condition = self._expression()
        self._expect_punct(Tk.RIGHT_PAREN, "after switch condition")

        # Cache the value being switched against so that it is only executed once.
        cache_var = Token.create_arbitrary(Tk.IDENTIFIER, f"__lox_temp_{id(condition):x}")
        cache_var_target = self._define_ident(cache_var)
        block = BlockStmt([
            VarStmt(cache_var, cache_var_target, condition)
        ])
        cached_condition = VariableExpr(cache_var, self._resolve_ident(cache_var))

        self._expect_next(Tk.LEFT_BRACE, "Expect '{' before switch arms")

        switch: Optional[IfStmt] = None
        inner_ref = switch  # Cache a reference to the innermost if statement.
        default_action: Optional[Stmt] = None

        # Build the tree of if statements.
        while self._tv.peek() != Tk.RIGHT_BRACE:
            arm_condition = self._expression()
            self._expect_next(Tk.EQUAL_GREATER, "Expect '=>' after switch arm")
            arm_action = self._statement()

            if isinstance(arm_condition, VariableExpr) and arm_condition.name.lexeme == "_":  # Found the default arm.
                if default_action is not None:  # If we've already got one, there's a problem.
                    raise LoxSyntaxError.at_token(arm_condition.name, "Cannot have more than one default case.")
                default_action = arm_action  # Otherwise, save it until the entire tree is built.
            else:
                arm = IfStmt(
                    BinaryExpr(Token.create_arbitrary(Tk.EQUAL_EQUAL, "=="), cached_condition, arm_condition),
                    arm_action,
                    None
                )
                if inner_ref is None:  # Initialize the first if statement if necessary.
                    switch = arm
                else:
                    inner_ref.else_branch = arm  # Add another if to the end of the tree.
                inner_ref = arm  # Cache the inner if statement to avoid tree transversal on the the next pass.

        self._expect_next(Tk.RIGHT_BRACE, "Expect '}' after switch arms")

        if switch is None:
            if default_action is not None:
                block.body.append(default_action)
        else:
            assert inner_ref is not None
            inner_ref.else_branch = default_action
            block.body.append(switch)
        return block

    def _return_statement_parselet(self) -> ReturnStmt:
        keyword = self._tv.peek_unwrap(-1)
        expr = self._expression() if self._tv.peek() != Tk.SEMICOLON else None
        self._expect_punct(Tk.SEMICOLON, "after return value")
        return ReturnStmt(keyword, expr)

    def _while_statement_parselet(self) -> WhileStmt:
        self._expect_punct(Tk.LEFT_PAREN, "after 'while'")
        condition = self._expression()
        self._expect_punct(Tk.RIGHT_PAREN, "after while condition")
        with self._scopes.scope():
            body = self._statement()
        return WhileStmt(condition, body)

    def _expression(self, min_precedence: Prec = Prec.NONE) -> Expr:
        """Pratt parser.

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
            self._expect_punct(Tk.RIGHT_PAREN, "after expression")
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
            left = VariableExpr(token, self._resolve_ident(token))
        else:
            raise LoxSyntaxError.at_token(token, "Expect expression.")

        # Parse the operator and the RHS, if possible.
        while self._has_next():
            op = self._tv.peek_unwrap()
            op_type = op.token_type

            if prec := OPERATOR_PRECEDENCE.get(op_type):  # Check if the operator is valid.
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
                    self._expect_punct(Tk.COLON, "in ternary if operator")

                if op_type not in {Tk.LEFT_PAREN}:  # Postfix operators do not have an RHS expression.
                    # Otherwise, parse the RHS up to the current operator's precedence,
                    # taking right associativity into account, if necessary.
                    right = self._expression(prec.adjust_for_operator_associativity(op_type))

                # Build the new LHS.
                if op_type is Tk.LEFT_PAREN:
                    left = CallExpr(left, op, list(self._parse_repeatedly(self._expression)))
                elif op_type is Tk.QUESTION:
                    left = TernaryIfExpr(left, middle, right)
                elif op_type is Tk.EQUAL:
                    left = self._assignment_expression_parselet(op, left, right)
                elif op_type in {Tk.AND, Tk.OR}:
                    left = LogicalExpr(op, left, right)
                else:
                    left = BinaryExpr(op, left, right)
            else:  # If it's not an operator, we're done.
                break

        return left

    def _assignment_expression_parselet(self, op: Token, left: Expr, right: Expr) -> AssignmentExpr:
        if isinstance(left, VariableExpr):
            return AssignmentExpr(left.name, left.mangled, right)
        raise LoxSyntaxError.at_token(op, "Invalid assignment target.")


__all__ = ("Parser",)