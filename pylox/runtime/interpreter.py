from contextlib import nullcontext
from operator import add, ge, gt, le, lt, mul
from operator import pow as op_pow
from operator import sub
from typing import Any, Callable, Dict, List, Sequence, Union

from pylox.language.lox_callable import LoxCallable, LoxFunction, LoxReturn
from pylox.language.lox_types import (LoxIdentifier, LoxObject, LoxPrimitive, lox_division, lox_equality,
                                      lox_object_to_str, lox_truth)
from pylox.lexing.token import Tk, Token
from pylox.parsing.expr import *
from pylox.parsing.stmt import *
from pylox.runtime.resolver import Resolver
from pylox.utilities import are_of_expected_type, dump_internal
from pylox.utilities.error import NOT_REACHED, LoxError, LoxErrorHandler, LoxRuntimeError
from pylox.utilities.stacked_map import StackedMap
from pylox.utilities.visitor import Visitor


class Interpreter(Visitor[Union[Expr, Stmt], Union[None, LoxObject]]):
    # pylint: disable=invalid-name
    _environment: StackedMap[LoxIdentifier, LoxObject]

    def __init__(self, error_handler: LoxErrorHandler, *, dump: bool = False) -> None:
        self._error_handler = error_handler
        self._resolver = Resolver()
        self.reinitialize_environment()
        self._dump = dump

    def interpret(self, ast: List[Stmt]) -> None:
        try:
            self._resolver.resolve(ast)
            if self._dump:
                dump_internal("AST", *ast)
            for stmt in ast:
                self._execute(stmt)
        except LoxError as error:
            self._error_handler.err(error)

    def reinitialize_environment(self) -> None:
        self._environment = StackedMap()

    # ~~~ Helper functions ~~~

    def _execute(self, stmt: Stmt) -> None:
        self.visit(stmt)

    def _evaluate(self, expr: Expr) -> LoxObject:
        return self.visit(expr)

    def _expect_number_operand(self, operator: Token, *operand: LoxObject) -> None:
        """Enforce that the `operand`s passed are numbers. Otherwise,
        emit an error at the given `operator` token."""
        if not are_of_expected_type({float}, *operand):
            raise LoxRuntimeError.at_token(
                operator,
                "Operand must be a number." if len(operand) == 1 else "Operands must be numbers.",
                fatal=True
            )

    def _expect_number_or_string_operand(self, operator: Token, *operand: LoxObject) -> None:
        """Enforce that the `operand`s passed are all numbers or all strings.
        Otherwise, emit an error at the given `operator` token."""
        if not are_of_expected_type({float, str}, *operand):
            raise LoxRuntimeError.at_token(operator, "Operands must be two numbers or two strings.", fatal=True)

    # ~~~ Callable interpreter ~~~

    def _call(self, callee: LoxCallable, arguments: Sequence[LoxObject]) -> LoxObject:
        try:
            assert callee.arity == len(arguments)
            with self._environment.graft(callee.environment), self._environment.scope():
                for param, arg in zip(callee.params, arguments):
                    assert param.target_id is not None
                    self._environment.define(param.target_id, arg)
                self._execute(callee.body)
        except LoxReturn as value:
            return value.value
        return None

    # ~~~ Statement interpreters ~~~

    def _visit_GroupingDirective__(self, stmt: GroupingDirective) -> None:
        with self._environment.scope() if isinstance(stmt, BlockStmt) else nullcontext():
            for inner_stmt in stmt.body:
                self._execute(inner_stmt)

    def _visit_ExpressionStmt__(self, stmt: ExpressionStmt) -> None:
        self._evaluate(stmt.expression)

    def _visit_FunctionDeclarationStmt__(self, stmt: FunctionDeclarationStmt) -> None:
        assert stmt.uniq_id is not None
        self._environment.define(stmt.uniq_id, LoxFunction(stmt, self._environment.tail()))

    def _visit_IfStmt__(self, stmt: IfStmt) -> None:
        if lox_truth(self._evaluate(stmt.condition)):
            self._execute(stmt.then_branch)
        elif stmt.else_branch:
            self._execute(stmt.else_branch)

    def _visit_PrintStmt__(self, stmt: PrintStmt) -> None:
        print(lox_object_to_str(self._evaluate(stmt.expression)))

    def _visit_VariableDeclarationStmt__(self, stmt: VariableDeclarationStmt) -> None:
        assert stmt.uniq_id is not None
        value: LoxObject = None
        if stmt.initializer is not None:
            value = self._evaluate(stmt.initializer)
        self._environment.define(stmt.uniq_id, value)

    def _visit_ReturnStmt__(self, stmt: ReturnStmt) -> None:
        if stmt.expression:
            raise LoxReturn(self._evaluate(stmt.expression))
        raise LoxReturn(None)

    def _visit_WhileStmt__(self, stmt: WhileStmt) -> None:
        while lox_truth(self._evaluate(stmt.condition)):
            self._execute(stmt.body)

    # ~~~ Expression interpreters ~~~

    def _visit_AssignmentExpr__(self, expr: AssignmentExpr) -> LoxObject:
        if expr.target_id is None:
            raise LoxRuntimeError.at_token(expr.name, f"Undefined variable '{expr.name.lexeme}'.", fatal=True)
        value = self._evaluate(expr.value)
        self._environment.assign(expr.target_id, value)
        return value

    def _visit_BinaryExpr__(self, expr: BinaryExpr) -> Union[bool, float, str]:
        """Evaluate the two operands, ensure that their types match, and finally
        apply the correct binary operation.

        The binary operations include comparisons, the four arithmetic operations,
        and string concatenation."""
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        ops: Dict[Tk, Callable[[Any, Any], Union[bool, float, str]]] = {
            # Mathematical operations:
            Tk.PLUS: add,
            Tk.MINUS: sub,
            Tk.STAR: mul,
            Tk.STAR_STAR: op_pow,
            Tk.SLASH: lox_division,
            # Equality:
            Tk.EQUAL_EQUAL: lox_equality,
            Tk.BANG_EQUAL: lambda l, r: not lox_equality(l, r),
            # Comparison:
            Tk.GREATER: gt,
            Tk.GREATER_EQUAL: ge,
            Tk.LESS: lt,
            Tk.LESS_EQUAL: le,
        }
        if (op := expr.operator.token_type) in ops:  # pylint: disable=superfluous-parens
            # Note that we do not do implicit casts. That Pandora's box is not to be opened...
            if op is Tk.PLUS:  # Used for both arithmetic addition and string concatenation.
                self._expect_number_or_string_operand(expr.operator, left, right)
            elif op in {Tk.BANG_EQUAL, Tk.EQUAL_EQUAL}:  # Equality comparisons are valid on all objects.
                pass
            else:  # Arithmetic operations and comparisons.
                self._expect_number_operand(expr.operator, left, right)
            return ops[op](left, right)

        raise NOT_REACHED

    def _visit_CallExpr__(self, expr: CallExpr) -> LoxObject:
        callee = self._evaluate(expr.callee)
        arguments = tuple(map(self._evaluate, expr.arguments))
        if not isinstance(callee, LoxCallable):
            raise LoxRuntimeError.at_token(expr.paren, "Can only call functions and classes.")
        if (found := len(arguments)) != (expected := callee.arity):
            raise LoxRuntimeError.at_token(expr.paren, f"Expected {expected} arguments but got {found}.")
        return self._call(callee, arguments)

    def _visit_GroupingExpr__(self, expr: GroupingExpr) -> LoxObject:
        """Evaluate a group by evaluating the expression contained within."""
        return self._evaluate(expr.expression)

    def _visit_LiteralExpr__(self, expr: LiteralExpr) -> LoxPrimitive:
        """A literal is evaluated by extracting its value."""
        return expr.value

    def _visit_LogicalExpr__(self, expr: LogicalExpr) -> LoxObject:
        left = self._evaluate(expr.left)
        if expr.operator.token_type is Tk.OR:
            if lox_truth(left):
                return left
        else:
            if not lox_truth(left):
                return left
        return self._evaluate(expr.right)

    def _visit_TernaryIfExpr__(self, expr: TernaryIfExpr) -> LoxObject:
        """A ternary if operator is evaluated with... of course, another ternary if operator."""
        return self._evaluate(
            expr.then_branch if lox_truth(self._evaluate(expr.condition))
            else expr.else_branch
        )

    def _visit_UnaryExpr__(self, expr: UnaryExpr) -> Union[bool, float]:
        """Evaluate the operand and then apply the correct unary operation.

        There are two unary operations: logical negation and arithmetic negation."""
        right = self._evaluate(expr.right)

        if (op := expr.operator.token_type) is Tk.BANG:
            return not lox_truth(right)
        if op is Tk.MINUS:
            self._expect_number_operand(expr.operator, right)
            return -right  # type: ignore  # Previous line ensures that right is of type float.

        raise NOT_REACHED

    def _visit_VariableExpr__(self, expr: VariableExpr) -> LoxObject:
        if expr.target_id is None:
            raise LoxRuntimeError.at_token(expr.name, f"Undefined variable '{expr.name.lexeme}'.", fatal=True)
        return self._environment.get(expr.target_id)
