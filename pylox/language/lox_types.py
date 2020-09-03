from enum import Enum, auto
from typing import TYPE_CHECKING, NewType, Optional, Union

if TYPE_CHECKING:
    from pylox.language.lox_callable import LoxCallable
    from pylox.language.lox_class import LoxClass, LoxInstance
    from pylox.parsing.expr import VariableExpr

LoxLiteral = Union[str, float]
LoxPrimitive = Union[float, str, bool, None]
LoxObject = Union[LoxPrimitive, "VariableExpr", "LoxCallable", "LoxInstance"]

LoxIdentifier = NewType("LoxIdentifier", int)


class FunctionKind(Enum):
    FUNCTION = "function"
    METHOD = "method"
    CONSTRUCTOR = auto()


def lox_is_valid_identifier_start(char: Optional[str]) -> bool:
    if char is None:
        return False
    return char.isalpha() or char == "_"


def lox_is_valid_identifier_name(char: Optional[str]) -> bool:
    if char is None:
        return False
    return lox_is_valid_identifier_start(char) or char.isdigit()


def lox_object_to_str(obj: LoxObject) -> str:
    """Represent a Lox object as a string."""
    if obj is None:
        return "nil"  # The null type is "nil" in Lox.
    string = str(obj)
    if isinstance(obj, float) and string.endswith(".0"):
        string = string[:-2]  # Output 100.0 as 100, etc.
    elif isinstance(obj, bool):
        string = string.lower()  # Convert "True" to "true", etc.
    return string


def lox_object_to_repr(obj: LoxObject) -> str:
    if obj is None:
        return "nil"
    string = str(obj)
    if isinstance(obj, bool):
        string = string.lower()
    elif isinstance(obj, str):
        string = f"'{string}'"
    return string


def lox_truth(obj: LoxObject) -> bool:
    """Evaluate the truthiness of a Lox object.

    `false` and `nil` are the only falsy objects."""
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    return True


def lox_equality(left: LoxObject, right: LoxObject) -> bool:
    """Evaluate if two Lox objects are equal."""
    if type(left) is type(right):
        return left == right
    return False


def lox_division(left: float, right: float) -> float:
    try:
        return left / right
    except ZeroDivisionError:
        return float("nan")
