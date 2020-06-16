import sys
from typing import Optional

from pylox.error import LoxErrorHandler, LoxExit
from pylox.interpreter import Interpreter
from pylox.parser import Parser
from pylox.scanner import Scanner

# pylint: disable=unused-variable


class Lox:
    PROMPT_CHARACTER = ">>> "
    DUMP_OPTIONS = ("tokens", "ast", "all")

    def __init__(self, dump_option: Optional[str] = None) -> None:
        self.error_handler = LoxErrorHandler()
        self.dump_option = dump_option

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
            dump=self.dump_option in ("tokens", "all")
        )
        tokens = scanner.scan_tokens()
        self.error_handler.checkpoint()
        parser = Parser(
            tokens,
            self.error_handler,
            dump=self.dump_option in ("ast", "all")
        )
        expression = parser.parse()
        self.error_handler.checkpoint()
        interpreter = Interpreter(self.error_handler)
        assert expression is not None
        interpreter.interpret(expression)
