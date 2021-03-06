import sys

from pylox.lexing.lexer import Lexer
from pylox.parsing.parser import Parser
from pylox.runtime.interpreter import Interpreter
from pylox.utilities.configuration import Debug
from pylox.utilities.error import LoxErrorHandler, LoxExit, catch_internal_error


class Lox:
    PROMPT_CHARACTER = ">>> "

    def __init__(self, debug_flags: Debug = Debug(0)) -> None:
        self.debug_flags = debug_flags
        self.error_handler = LoxErrorHandler(self.debug_flags)
        self.interpreter = Interpreter(self.error_handler, dump=bool(self.debug_flags & Debug.DUMP_AST))

    def run_file(self, path: str) -> None:
        with open(path, 'r') as fil:
            self.run(fil.read())

    def run_interactive(self) -> None:
        import readline  # pylint: disable=unused-import, import-outside-toplevel
        while True:
            try:
                self.run(input(self.PROMPT_CHARACTER))
            except LoxExit:
                continue
            except (KeyboardInterrupt, EOFError):  # Exit gracefully on ctrl-c or ctrl-d.
                sys.exit(0)

    def run(self, source: str) -> None:
        with catch_internal_error(dump_backtrace=bool(self.debug_flags & Debug.BACKTRACE), ignore_types=(LoxExit,)):
            source = source.replace("\r\n", "\n")
            self.error_handler.set_source(source)

            tokens = Lexer(source, self.error_handler, debug_flags=self.debug_flags).lex_tokens()

            self.error_handler.checkpoint()
            if self.debug_flags & Debug.NO_PARSE:
                raise LoxExit(0)
            statements = Parser(tokens, self.error_handler).parse()

            self.error_handler.checkpoint()
            if self.debug_flags & Debug.NO_INTERPRET:
                raise LoxExit(0)
            self.interpreter.interpret(statements)
