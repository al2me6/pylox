import sys

from pylox.error import LoxErrorHandler, LoxExit
from pylox.interpreter import Interpreter
from pylox.parser import Parser
from pylox.scanner import Scanner
from pylox.utilities import Debug


class Lox:
    PROMPT_CHARACTER = ">>> "

    def __init__(self, debug_flags: Debug = Debug(0)) -> None:
        self.error_handler = LoxErrorHandler()
        self.debug_flags = debug_flags
        self.interpreter = Interpreter(self.error_handler)

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
        source = source.replace("\r\n", "\n")
        self.error_handler.set_source(source)

        tokens = Scanner(
            source,
            self.error_handler,
            debug_flags=self.debug_flags
        ).scan_tokens()

        self.error_handler.checkpoint()
        if self.debug_flags & Debug.NO_PARSE:
            raise LoxExit(0)
        statements = Parser(
            tokens,
            self.error_handler,
            dump=bool(self.debug_flags & Debug.DUMP_AST)
        ).parse()

        self.error_handler.checkpoint()
        if self.debug_flags & Debug.NO_INTERPRET:
            raise LoxExit(0)
        self.interpreter.interpret(statements)
