from operator import add, ge, gt, le, lt, mul, sub, truediv
from typing import Any, Set, Type

from pylox.error import LoxErrorHandler, LoxRuntimeError
from pylox.expr import *
from pylox.token import Tk, Token
from pylox.utilities import NOT_REACHED
from pylox.visitor import Visitor


def _check_types(expected_types: Set[Type], *obj: Any) -> bool:
    """Check if the `obj`s passed are all of one of the expected types."""
    for expected_type in expected_types:
        if all(map(lambda o: isinstance(o, expected_type), obj)):  # pylint: disable=cell-var-from-loop
            return True
    return False


def _truthiness(obj: Any) -> bool:
    """Evaluate the truthiness of a Lox object.

    `false` and `nil` are the only falsy objects."""
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    return True


def _equality(left: Any, right: Any) -> bool:
    """Evaluate if two Lox objects are equal."""
    if left is None:
        if right is None:
            return True
        return False
    return left == right


def _to_text(obj: Any) -> str:
    """Convert a Lox object to a string."""
    if obj is None:
        return "nil"  # The null type is "nil" in Lox.
    text = str(obj)
    if isinstance(obj, float) and text.endswith(".0"):
        text = text[-3]  # Output 100.0 as 100, etc.
    elif isinstance(obj, bool):
        text = text.lower()  # Convert "True" to "true", etc.
    return text


class Interpreter(Visitor):
    # pylint: disable=invalid-name

    def __init__(self, error_handler: LoxErrorHandler) -> None:
        self._error_handler = error_handler

    def interpret(self, expr: Expr) -> None:
        try:
            print(_to_text(self._evaluate(expr)))
        except LoxRuntimeError as error:
            self._error_handler.err(error)

    # ~~~ Helper functions ~~~

    def _evaluate(self, expr: Expr) -> Any:
        return expr.accept(self)

    def _expect_number_operand(self, operator: Token, *operand: Any) -> None:
        """Enforce that the `operand`s passed are numbers. Otherwise,
        emit an error at the given `operator` token."""
        if not _check_types({float}, *operand):
            raise LoxRuntimeError.at_token(operator, "Operands must be numbers.", fatal=True)

    def _expect_number_or_string_operand(self, operator: Token, *operand: Any) -> None:
        """Enforce that the `operand`s passed are all numbers or all strings. Otherwise,
        emit an error at the given `operator` token."""
        if not _check_types({float, str}, *operand):
            raise LoxRuntimeError.at_token(operator, "Operands must both be numbers or both be strings.", fatal=True)

    # ~~~ Interpreters ~~~

    def _visit_LiteralExpr__(self, expr: LiteralExpr) -> LoxLiteral:
        """A literal is evaluated by extracting its value."""
        return expr.value

    def _visit_GroupingExpr__(self, expr: GroupingExpr) -> Any:
        """Evaluate a group by evaluating the expression contained within."""
        return self._evaluate(expr.expression)

    def _visit_UnaryExpr__(self, expr: UnaryExpr) -> Any:
        """Evaluate the operand and then apply the correct unary operation.

        There are two unary operations: logical negation and arithmetic negation."""
        right = self._evaluate(expr.right)

        if (op := expr.operator.token_type) is Tk.BANG:
            return not _truthiness(right)
        if op is Tk.MINUS:
            self._expect_number_operand(expr.operator, right)
            return -right

        raise NOT_REACHED

    def _visit_BinaryExpr__(self, expr: BinaryExpr) -> Any:
        """Evaluate the two operands, ensure that their types match, and finally
        apply the correct binary operation.

        The binary operations include comparisons, the four arithmetic operations,
        and string concatenation."""
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        ops = {
            Tk.PLUS: add,
            Tk.MINUS: sub,
            Tk.STAR: mul,
            Tk.SLASH: truediv,
            Tk.GREATER: gt,
            Tk.GREATER_EQUAL: ge,
            Tk.LESS: lt,
            Tk.LESS_EQUAL: le,
            Tk.EQUAL_EQUAL: _equality,
            Tk.BANG_EQUAL: lambda l, r: not _equality(l, r),
        }
        if (op := expr.operator.token_type) in ops:
            # Note that we do not do implicit casts. That Pandora's box is not to be opened...
            if op is Tk.PLUS:  # Used for both arithmetic addition and string concatenation.
                self._expect_number_or_string_operand(expr.operator, left, right)
            elif op in {Tk.BANG_EQUAL, Tk.EQUAL_EQUAL}:  # Equality comparisons are valid on all objects.
                pass
            else:  # Arithmetic operations and comparisons.
                self._expect_number_operand(expr.operator, left, right)
            return ops[op](left, right)

        raise NOT_REACHED
