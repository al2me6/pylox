from __future__ import annotations

from enum import IntEnum, auto
from typing import Callable, Iterator, List, Optional, TypeVar, Union

from pylox.language.lox_types import FunctionKind
from pylox.lexing.token import Tk, Token
from pylox.parsing.expr import *
from pylox.parsing.stmt import *
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
    Tk.EQUAL: Prec.ASSIGNMENT,
    Tk.QUESTION: Prec.TERNARY,
    Tk.OR: Prec.OR,
    Tk.AND: Prec.AND,
    Tk.BANG_EQUAL: Prec.EQUALITY,
    Tk.EQUAL_EQUAL: Prec.EQUALITY,
    Tk.LESS_EQUAL: Prec.COMPARISON,
    Tk.LESS: Prec.COMPARISON,
    Tk.GREATER_EQUAL: Prec.COMPARISON,
    Tk.GREATER: Prec.COMPARISON,
    Tk.MINUS: Prec.TERM,
    Tk.PLUS: Prec.TERM,
    Tk.SLASH: Prec.FACTOR,
    Tk.STAR: Prec.FACTOR,
    Tk.STAR_STAR: Prec.EXP,
    Tk.DOT: Prec.CALL,
    Tk.PAREN_LEFT: Prec.CALL,
}


class Parser:
    """A simple Pratt parser.

    Its logic is derived from a combination of `jlox` and `clox`, though the
    implementation is motivated by Aleksey Kladov's article on the subject:
    https://matklad.github.io/2020/04/13/simple-but-powerful-pratt-parsing.html.
    """

    def __init__(self, tokens: List[Token], error_handler: LoxErrorHandler) -> None:
        self._tv = StreamView(tokens)
        self._error_handler = error_handler
        self._ast: List[Stmt] = list()

    def parse(self) -> List[Stmt]:
        while self._has_next():
            if declaration := self._declaration():
                self._ast.append(declaration)
        return self._ast

    # ~~~ Helper functions ~~~

    def _has_next(self) -> bool:
        """Wrapper around `StreamView.has_next()` that does not count `Tk.EOF`."""
        if self._tv.has_next():
            if self._tv.peek_unwrap().token_type is not Tk.EOF:
                return True
        return False

    def _expect_next(self, expected: Tk, message: str) -> Token:
        """Wrapper around `StreamView.advance_if_match()`; raise error with `message`
        if the desired token is not found."""
        if self._tv.match(expected):
            return self._tv.advance()
        raise LoxSyntaxError.at_token(self._tv.peek_unwrap(), message)

    def _expect_punct(self, symbol: Tk, message: str) -> None:
        """Expect a punctuation token with streamlined error reporting.

        :param symbol: punctuation to expect (ex. Tk.COMMA)
        :type symbol: Tk
        :param message: where the punctuation should have been found (ex. "after statement")
        :type message: str
        """
        self._expect_next(symbol, f"Expect '{symbol.value}' {message}.")

    def _synchronize(self) -> None:
        """Drop tokens until parsing can be safely resumed, so that the maximum number of errors
        can be reported (as opposed to bailing on the first error encountered)."""
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

    _T = TypeVar("_T")

    def _parse_repeatedly(
            self, parselet: Callable[[], Union[_T, Optional[_T]]],
            *,
            separator: Optional[Tk] = Tk.COMMA,
            terminator: Tk = Tk.PAREN_RIGHT,
            terminator_expect_message: str = "after expression"
    ) -> Iterator[_T]:
        """Repeatedly and *lazily* parse items of a certain type until a marker token is reached.

        :param parselet: parser for a single item (can return None; will be dropped)
        :type parselet: Callable[[], Union[T, Optional[_T]]]
        :param separator: separator between each item, defaults to Tk.COMMA
        :type separator: Optional[Tk], optional
        :param terminator: end marker, defaults to Tk.PAREN_RIGHT
        :type terminator: Tk, optional
        :param terminator_expect_message: error message if the marker is not found, defaults to "after expression"
        :type terminator_expect_message: str, optional
        :rtype: Iterator[_T]
        """
        while self._has_next():
            if self._tv.peek_unwrap().token_type is terminator:
                break
            if result := parselet():
                yield result
            if separator:
                if not self._tv.advance_if_match(separator):
                    break
        self._expect_punct(terminator, terminator_expect_message)

    def _parse_statements_in_block(self) -> Iterator[Stmt]:
        """*Lazily* parse productions of the form `STMT* "}" ;`, yielding each enclosed statement."""
        return self._parse_repeatedly(
            self._declaration,
            separator=None,
            terminator=Tk.BRACE_RIGHT,
            terminator_expect_message="after block"
        )

    # ~~~ Parsers ~~~

    def _declaration(self) -> Optional[Stmt]:
        decl: Optional[Stmt]
        try:
            if self._tv.advance_if_match(Tk.VAR):
                decl = self._variable_declaration_parselet()
            elif self._tv.advance_if_match(Tk.CLASS):
                decl = self._class_declaration_parselet()
            elif self._tv.peek() == Tk.FUN and self._tv.peek(1) == Tk.IDENTIFIER:
                self._tv.advance()
                decl = self._named_callable_parselet(FunctionKind.FUNCTION)
            else:
                decl = self._statement()
        except LoxSyntaxError as error:
            self._error_handler.err(error)
            self._synchronize()
            decl = None

        return decl

    def _class_declaration_parselet(self) -> ClassDeclarationStmt:
        name = self._expect_next(Tk.IDENTIFIER, "Expect class name.")
        self._expect_punct(Tk.BRACE_LEFT, "before class body")
        instance_variables = list(self._parse_repeatedly(
            lambda: (
                self._named_callable_parselet(FunctionKind.METHOD) if self._tv.peek(1) == Tk.PAREN_LEFT
                else self._variable_declaration_parselet()
            ),
            separator=None,
            terminator=Tk.BRACE_RIGHT,
            terminator_expect_message="after class body"
        ))
        return ClassDeclarationStmt(name, instance_variables)

    def _named_callable_parselet(self, kind: FunctionKind) -> VariableDeclarationStmt:
        """Parse callable (function and method) declarations.

        Production: `"fun"? IDENT ANONYMOUS_FUNCTION_EXPR ;`
        ```
        """
        name = self._expect_next(Tk.IDENTIFIER, f"Expect {kind.value} name.")
        body = self._anonymous_function_expression_parselet(kind)
        return VariableDeclarationStmt(name, body)

    def _variable_declaration_parselet(self) -> VariableDeclarationStmt:
        """A variable declared without assignment is implicitly `nil`.

        Production: `"var" ( "=" EXPR )? ";" ;`
        """
        name = self._expect_next(Tk.IDENTIFIER, "Expect variable name.")
        expr = self._expression() if self._tv.advance_if_match(Tk.EQUAL) else None
        self._expect_punct(Tk.SEMICOLON, "after expression")
        return VariableDeclarationStmt(name, expr)

    def _statement(self) -> Stmt:
        # When is Python 3.10 coming out again???
        stmt: Stmt
        if self._tv.advance_if_match(Tk.FOR):
            stmt = self._for_statement_parselet()
        elif self._tv.advance_if_match(Tk.IF):
            stmt = self._if_statement_parselet()
        elif self._tv.advance_if_match(Tk.BRACE_LEFT):
            stmt = BlockStmt(*self._parse_statements_in_block())
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

    def _expression_statement_parselet(self) -> ExpressionStmt:
        """Production: `EXPR ";" ;`"""
        stmt = ExpressionStmt(self._expression())
        self._expect_punct(Tk.SEMICOLON, "after expression")
        return stmt

    def _for_statement_parselet(self) -> Stmt:
        """Parse C-style for loops by desugaring them into while loops.

        Note that the loop variable is reused! Beware when passing said
        variable by reference for use later.

        The statement:

        ```
        for(var i = 0; i <= 4; i = i + 1) {
            // Loop body.
        }
        ```

        desugars to:

        ```
        {
            var i = 0;
            while(i <= 4) {
                // Loop body.
                i = i + 1;
            }
        }

        Production: `"for" "(" ( VAR_STMT | EXPR )? ";" EXPR? ";" EXPR? ")" STMT ;`
        ```
        """
        self._expect_punct(Tk.PAREN_LEFT, "after 'for'")

        initializer: Optional[Stmt]
        if self._tv.advance_if_match(Tk.SEMICOLON):
            initializer = None
        elif self._tv.advance_if_match(Tk.VAR):
            initializer = self._variable_declaration_parselet()
        else:
            initializer = self._expression_statement_parselet()

        condition = self._expression() if self._tv.peek() != Tk.SEMICOLON else LiteralExpr(True)
        self._expect_punct(Tk.SEMICOLON, "after loop condition")

        increment = self._expression() if self._tv.peek() != Tk.PAREN_RIGHT else None
        self._expect_punct(Tk.PAREN_RIGHT, "after for clauses")

        body = self._statement()

        if increment:
            body = GroupingDirective(body, ExpressionStmt(increment))
        body = WhileStmt(condition, BlockStmt(body))
        if initializer:
            body = BlockStmt(initializer, body)

        return body

    def _if_statement_parselet(self) -> IfStmt:
        """Note that branches are scoped. That is, variables instantiated inside
        the if statement do not get added to the parent scope. This is to ensure
        that the variable would always be defined, no matter which branch of
        the if statement is taken.

        Production: `"if" "(" EXPR ")" STMT ( "else" STMT )? ;`
        """
        self._expect_punct(Tk.PAREN_LEFT, "after 'if'")
        condition = self._expression()
        self._expect_punct(Tk.PAREN_RIGHT, "after if condition")
        then_branch = BlockStmt(self._statement())
        else_branch = BlockStmt(self._statement()) if self._tv.advance_if_match(Tk.ELSE) else None
        return IfStmt(condition, then_branch, else_branch)

    def _switch_statement_parselet(self) -> GroupingDirective:
        # TODO: reimplement switches without desugaring and allow matching multiple conditions to one action.
        self._expect_punct(Tk.PAREN_LEFT, "after 'switch'")
        condition = self._expression()
        self._expect_punct(Tk.PAREN_RIGHT, "after switch condition")

        # Cache the value being switched against so that it is only executed once.
        cache_var = Token.create_arbitrary(Tk.IDENTIFIER, f"__lox_temp_{id(condition):x}")
        block = BlockStmt(VariableDeclarationStmt(cache_var, condition))
        cached_condition = VariableExpr(cache_var)

        self._expect_next(Tk.BRACE_LEFT, "Expect '{' before switch arms")

        switch: Optional[IfStmt] = None
        inner_ref = switch  # Cache a reference to the innermost if statement.
        default_action: Optional[Stmt] = None

        # Build the tree of if statements.
        while self._tv.peek() != Tk.BRACE_RIGHT:
            arm_condition = self._expression()
            self._expect_next(Tk.EQUAL_GREATER, "Expect '=>' after switch arm")
            arm_action = self._statement()

            if isinstance(arm_condition, VariableExpr) and arm_condition.target.lexeme == "_":  # Found the default arm.
                if default_action is not None:  # If we've already got one, there's a problem.
                    raise LoxSyntaxError.at_token(arm_condition.target, "Cannot have more than one default case.")
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

        self._expect_next(Tk.BRACE_RIGHT, "Expect '}' after switch arms")

        if switch is None:
            if default_action is not None:
                block.body.append(default_action)
        else:
            assert inner_ref is not None
            inner_ref.else_branch = default_action
            block.body.append(switch)
        return block

    def _return_statement_parselet(self) -> ReturnStmt:
        """Production: `"return" EXPR? ";" ;`"""
        keyword = self._tv.peek_unwrap(-1)
        expr = self._expression() if self._tv.peek() != Tk.SEMICOLON else None
        self._expect_punct(Tk.SEMICOLON, "after return value")
        return ReturnStmt(keyword, expr)

    def _while_statement_parselet(self) -> WhileStmt:
        """Note that the body of a while statement is always scoped.

        Production: `"while" "(" EXPR ")" STMT ;`
        """
        self._expect_punct(Tk.PAREN_LEFT, "after 'while'")
        condition = self._expression()
        self._expect_punct(Tk.PAREN_RIGHT, "after while condition")
        return WhileStmt(condition, BlockStmt(self._statement()))

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
        # Parse prefix operators and primary expressions into the LHS.
        token = self._tv.advance()
        left: Expr
        if (token_type := token.token_type) is Tk.PAREN_LEFT:
            enclosed = self._expression()
            self._expect_punct(Tk.PAREN_RIGHT, "after expression")
            left = GroupingExpr(enclosed)
        elif token_type in {Tk.BANG, Tk.MINUS}:
            left = UnaryExpr(token, self._expression(Prec.UNARY))
        elif token_type in {Tk.FALSE, Tk.TRUE, Tk.NIL, Tk.NUMBER, Tk.STRING}:
            left = LiteralExpr({
                Tk.FALSE: False,
                Tk.TRUE: True,
                Tk.NIL: None
            }.get(token_type, token.literal))
        elif token_type is Tk.FUN:
            left = self._anonymous_function_expression_parselet(FunctionKind.FUNCTION)
        elif token_type is Tk.IDENTIFIER:
            left = VariableExpr(token)
        elif token_type is Tk.THIS:
            left = ThisExpr(token)
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

                # Postfix operators do not have an RHS expression.
                if op_type not in {Tk.DOT, Tk.PAREN_LEFT}:
                    # Otherwise, parse the RHS up to the current operator's precedence,
                    # taking right associativity into account, if necessary.
                    right = self._expression(prec.adjust_for_operator_associativity(op_type))

                # Build the new LHS.
                if op_type in {Tk.AND, Tk.OR}:
                    left = LogicalExpr(op, left, right)
                elif op_type is Tk.DOT:
                    left = self._attribute_access_expression_parselet(left)
                elif op_type is Tk.EQUAL:
                    left = self._assignment_expression_parselet(op, left, right)
                elif op_type is Tk.PAREN_LEFT:
                    left = CallExpr(left, op, list(self._parse_repeatedly(self._expression)))
                elif op_type is Tk.QUESTION:
                    left = TernaryIfExpr(left, middle, right)
                else:
                    left = BinaryExpr(op, left, right)
            else:  # If it's not an operator, we're done.
                break

        return left

    def _anonymous_function_expression_parselet(self, kind: FunctionKind) -> AnonymousFunctionExpr:
        """Parse the arguments and body of a function.

        Note that the values of the function's parameters will be inserted
        into the top of the function body when executed.

        When ran, the function:

        ```
        fun foo(bar, baz) {
            return bar * 2 + baz;
        }
        ```

        is executed as:

        ```
        {
            var bar = SOME_VALUE;
            var baz = SOME_OTHER_VALUE;
            return var * 2 + baz;
        }

        Production: `"(" IDENT? ( "," IDENT )* ")" "{" STMT* "}" ;`
        """
        self._expect_punct(Tk.PAREN_LEFT, f"before {kind.value} arguments")
        params = list(self._parse_repeatedly(
            lambda: VariableExpr(self._expect_next(Tk.IDENTIFIER, "Expect parameter name.")),
            terminator_expect_message="after parameters"
        ))
        self._expect_punct(Tk.BRACE_LEFT, f"before {kind} body")
        body = GroupingDirective(*self._parse_statements_in_block())
        return AnonymousFunctionExpr(params, body, kind)

    def _assignment_expression_parselet(
            self,
            op: Token,
            left: Expr,
            right: Expr
    ) -> Union[AssignmentExpr, DynamicAssignmentExpr]:
        if isinstance(left, VariableExpr):
            return AssignmentExpr(left.target, right)
        if isinstance(left, AttributeAccessExpr):
            return DynamicAssignmentExpr(left, right)
        raise LoxSyntaxError.at_token(op, "Invalid assignment target.")

    def _attribute_access_expression_parselet(self, left: Expr) -> AttributeAccessExpr:
        attr_name = self._expect_next(Tk.IDENTIFIER, "Expect property name after '.'.")
        return AttributeAccessExpr(left, attr_name)


__all__ = ("Parser",)
