from contextlib import contextmanager
from operator import add, ge, gt, le, lt, mul, sub
from typing import Any, Callable, Dict, List, Union

from pylox.environment import Environment
from pylox.error import LoxErrorHandler, LoxRuntimeError
from pylox.expr import *
from pylox.lox_types import LoxObject, LoxPrimitive, lox_division, lox_equality, lox_object_to_str, lox_truth
from pylox.stmt import *
from pylox.token import Tk, Token
from pylox.utilities import NOT_REACHED, are_of_expected_type
from pylox.visitor import Visitor


class Interpreter(Visitor):
    # pylint: disable=invalid-name
    _environment: Environment

    def __init__(self, error_handler: LoxErrorHandler) -> None:
        self._error_handler = error_handler
        self.reset_environment()

    def interpret(self, stmts: List[Stmt]) -> None:
        try:
            for stmt in stmts:
                self._execute(stmt)
        except LoxRuntimeError as error:
            self._error_handler.err(error)

    def reset_environment(self) -> None:
        self._environment = self._initialize_environment()

    # ~~~ Helper functions ~~~

    def _initialize_environment(self) -> Environment:
        return Environment()

    def _execute(self, stmt: Stmt) -> None:
        stmt.accept(self)

    def _evaluate(self, expr: Expr) -> LoxObject:
        return expr.accept(self)  # type: ignore

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

    @contextmanager
    def sub_environment(self):  # type: ignore  # How to type this?
        # TODO: verify ownership
        outer = self._environment
        self._environment = Environment(outer)
        yield
        self._environment = outer

    # ~~~ Statement interpreters ~~~

    def _visit_BlockStmt__(self, stmt: BlockStmt) -> None:
        with self.sub_environment():
            for inner_stmt in stmt.statements:
                self._execute(inner_stmt)

    def _visit_ExpressionStmt__(self, stmt: ExpressionStmt) -> None:
        self._evaluate(stmt.expression)

    def _visit_IfStmt__(self, stmt: IfStmt) -> None:
        if lox_truth(self._evaluate(stmt.condition)):
            self._execute(stmt.then_branch)
        elif stmt.else_branch:
            self._execute(stmt.else_branch)

    def _visit_PrintStmt__(self, stmt: PrintStmt) -> None:
        print(lox_object_to_str(self._evaluate(stmt.expression)))

    def _visit_VarStmt__(self, stmt: VarStmt) -> None:
        value: LoxObject = None
        if stmt.initializer is not None:
            value = self._evaluate(stmt.initializer)
        self._environment.define(stmt.name.lexeme, value)

    def _visit_WhileStmt__(self, stmt: WhileStmt) -> None:
        while lox_truth(self._evaluate(stmt.condition)):
            self._execute(stmt.body)

    # ~~~ Expression interpreters ~~~

    def _visit_AssignmentExpr__(self, expr: AssignmentExpr) -> LoxObject:
        value = self._evaluate(expr.value)
        self._environment.assign(expr.name, value)
        return value

    def _visit_BinaryExpr__(self, expr: BinaryExpr) -> Union[bool, float, str]:
        """Evaluate the two operands, ensure that their types match, and finally
        apply the correct binary operation.

        The binary operations include comparisons, the four arithmetic operations,
        and string concatenation."""
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        ops: Dict[Tk, Callable[[Any, Any], Union[bool, float, str]]] = {
            Tk.PLUS: add,
            Tk.MINUS: sub,
            Tk.STAR: mul,
            Tk.STAR_STAR: pow,
            Tk.SLASH: lox_division,
            Tk.GREATER: gt,
            Tk.GREATER_EQUAL: ge,
            Tk.LESS: lt,
            Tk.LESS_EQUAL: le,
            Tk.EQUAL_EQUAL: lox_equality,
            Tk.BANG_EQUAL: lambda l, r: not lox_equality(l, r),
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
        return self._environment.get(expr.name)
