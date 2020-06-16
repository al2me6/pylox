import argparse
import sys

from pylox.error import LoxErrorHandler, LoxExit
from pylox.interpreter import Interpreter
from pylox.parser import Parser
from pylox.scanner import Scanner

# pylint: disable=unused-variable


class Lox:
    PROMPT_CHARACTER = ">>> "
    DUMP_OPTIONS = ("tokens", "ast", "all")

    def __init__(self) -> None:
        self.error_handler = LoxErrorHandler()

        parser = argparse.ArgumentParser(
            prog="pylox",
            description="Yet another implementation of the Lox interpreter in Python",
            allow_abbrev=False
        )
        parser.add_argument(
            "source",
            metavar="FILE",
            nargs="?",
            type=argparse.FileType("r"),
            default=None,
            help="the .lox file to interpret, default to interactive mode"
        )
        parser.add_argument(
            "--dump",
            choices=self.DUMP_OPTIONS,
            metavar="|".join(self.DUMP_OPTIONS),
            help="dump the internal state of the interpreter"
        )
        (self.args, self.extra_args) = parser.parse_known_args()

        if self.args.source:
            self.run_file()
        else:
            self.run_interactive()

    def run_file(self) -> None:
        try:
            source = self.args.source.read()
        finally:
            self.args.source.close()
        self.run(source)

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
            dump=self.args.dump in ("tokens", "all")
        )
        tokens = scanner.scan_tokens()
        self.error_handler.checkpoint()
        parser = Parser(
            tokens,
            self.error_handler,
            dump=self.args.dump in ("ast", "all")
        )
        expression = parser.parse()
        self.error_handler.checkpoint()
        interpreter = Interpreter(self.error_handler)
        assert expression is not None
        interpreter.interpret(expression)
