import sys
from functools import reduce

from pylox.error import LoxErrorHandler, LoxExit
from pylox.interpreter import Interpreter
from pylox.parser import Parser
from pylox.scanner import Scanner
from pylox.utilities import Debug

# pylint: disable=unused-variable


class Lox:
    PROMPT_CHARACTER = ">>> "

    def __init__(self, debug_flags: Debug = Debug(0)) -> None:
        self.error_handler = LoxErrorHandler()
        self.debug_flags = debug_flags

    def run_file(self, path: str) -> None:
        with open(path, 'r') as fil:
            self.run(fil.read())

    def run_interactive(self) -> None:
        while True:
            try:
                self.run(input(self.PROMPT_CHARACTER))
            except LoxExit:
                continue
            except (KeyboardInterrupt, EOFError):  # Exit gracefully on ctrl-c or ctrl-d.
                sys.exit(0)

    def run(self, source: str) -> None:
        self.error_handler.set_source(source)
        scanner = Scanner(
            source,
            self.error_handler,
            dump=bool(self.debug_flags & Debug.DUMP_TOKENS)
        )
        tokens = scanner.scan_tokens()
        if (self.debug_flags & Debug.NO_PARSE):
            sys.exit(0)
        self.error_handler.checkpoint()
        parser = Parser(
            tokens,
            self.error_handler,
            dump=bool(self.debug_flags & Debug.DUMP_AST)
        )
        expression = parser.parse()
        self.error_handler.checkpoint()
        if (self.debug_flags & Debug.NO_INTERPRET):
            sys.exit(0)
        interpreter = Interpreter(self.error_handler)
        assert expression is not None
        interpreter.interpret(expression)
