from enum import Flag, auto


class Debug(Flag):
    DUMP_TOKENS = auto()
    DUMP_AST = auto()
    NO_PARSE = auto()
    NO_INTERPRET = auto()
    JAVA_STYLE_TOKENS = auto()
    REDUCED_ERROR_REPORTING = auto()
    BACKTRACE = auto()
