from operator import add, ge, gt, le, lt, mul, sub, truediv
from typing import Any, Set, Type

from pylox.error import LoxErrorHandler, LoxRuntimeError
from pylox.expr import *
from pylox.token import Token
from pylox.token import TokenType as TT
from pylox.utilities import NOT_REACHED
from pylox.visitor import Visitor


def _check_types(types: Set[Type], *obj: Any) -> bool:
    for _type in types:
        if all(map(lambda o: isinstance(o, _type), obj)):  # pylint: disable=cell-var-from-loop
            return True
    return False


def _truthiness(obj: Any) -> bool:
    """Evaluate the truthiness of a Lox object

    `false` and `nil` are the only falsy objects."""
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    return True


def _equality(left: Any, right: Any) -> bool:
    if left is None:
        if right is None:
            return True
        return False
    return left == right


def _to_text(obj: Any) -> str:
    if obj is None:
        return "nil"
    text = str(obj)
    if isinstance(obj, float) and text.endswith(".0"):
        text = text[-3]  # output 100.0 as 100, etc.
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

    # ~~~ helper functions ~~~

    def _evaluate(self, expr: Expr) -> Any:
        return expr.accept(self)

    def _expect_number_operand(self, operator: Token, *operand: Any) -> None:
        if not _check_types({float}, *operand):
            raise LoxRuntimeError.at_token(operator, "Operands must be numbers", fatal=True)

    # ~~~ interpreters ~~~

    def _visit_LiteralExpr__(self, expr: LiteralExpr) -> Any:
        return expr.value

    def _visit_GroupingExpr__(self, expr: GroupingExpr) -> Any:
        return self._evaluate(expr.expression)

    def _visit_UnaryExpr__(self, expr: UnaryExpr) -> LoxLiteral:
        right = self._evaluate(expr.right)

        if (case := expr.operator.token_type) is TT.BANG:
            return not _truthiness(right)
        if case is TT.MINUS:
            self._expect_number_operand(expr.operator, right)
            return -right

        assert NOT_REACHED
        return None

    def _visit_BinaryExpr__(self, expr: BinaryExpr) -> Any:
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        switch = {
            TT.PLUS: add,
            TT.MINUS: sub,
            TT.STAR: mul,
            TT.SLASH: truediv,
            TT.GREATER: gt,
            TT.GREATER_EQUAL: ge,
            TT.LESS: lt,
            TT.LESS_EQUAL: le,
            TT.EQUAL_EQUAL: _equality,
            TT.BANG_EQUAL: lambda left, right: not _equality(left, right),
        }
        if (case := expr.operator.token_type) in switch:
            if case is TT.PLUS:
                if not _check_types({float, str}, left, right):
                    raise LoxRuntimeError.at_token(expr.operator, "Operands must be numbers or strings", fatal=True)
            else:
                self._expect_number_operand(expr.operator, left, right)
            return switch[case](left, right)

        assert NOT_REACHED
        return None
