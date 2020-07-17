from __future__ import annotations

from abc import ABC
from typing import Iterator, Tuple, Type

from pylox.token import Token
from pylox.utilities import Debug, eprint


class LoxExit(SystemExit):
    """System exit requested by pylox due to error in input."""


class LoxError(RuntimeError, ABC):
    def __init__(
            self,
            offset: int,
            message: str,
            *,
            length: int = 1,
            fatal: bool = False
    ) -> None:
        """An error generated by pylox due to errors in Lox code.

        :param offset: offset from start of source stream
        :type offset: int
        :param message: error message
        :type message: str
        :param length: length of error marker, defaults to 1
        :type length: int, optional
        :param fatal: whether immediate exit is necessary, defaults to False
        :type fatal: bool, optional
        """
        super().__init__(f"{message} at offset {offset}")
        self.message = message
        self.offset = offset
        self.length = length
        self.fatal = fatal

    @classmethod
    def at_token(cls, token: Token, message: str, *, fatal: bool = False) -> LoxError:
        """Generate an error at a specific token.

        :param token: token at which error occurred
        :type token: Token
        :param message: message describing error
        :type message: str
        :param fatal: whether immediate exit is necessary, defaults to False
        :type fatal: bool, optional
        """
        length = len(token.lexeme) if token.lexeme else 1
        return cls(token.offset, message, length=length, fatal=fatal)


class LoxSyntaxError(LoxError):
    pass


class LoxRuntimeError(LoxError):
    pass


class LoxErrorHandler:
    LINE_NUMBER_SEPARATOR = " | "
    ERROR_MARKER = "^"

    def __init__(self, debug_flags: Debug) -> None:
        self.error_state = False
        self._source = "\0"
        self._debug_flags = debug_flags

    def clear_errors(self) -> None:
        self.error_state = False

    def set_source(self, source: str) -> None:
        self._source = source + "\0"
        self.clear_errors()

    def err(self, error: LoxError) -> None:
        """Report an error to stderr.

        :param error: error object containing error details
        :type error: LoxError
        """
        self.error_state = True  # TODO: track syntax vs runtime error and exit with corresponding error code.
        self._report(type(error).__name__, error.message, error.length, error.offset)
        if error.fatal:  # Force immediate exit.
            self.checkpoint()

    def checkpoint(self) -> None:
        """Exit if an error has occurred before the checkpoint."""
        if self.error_state:
            raise LoxExit(1)

    def _source_as_lines(self) -> Iterator[Tuple[int, int, str]]:
        """Split the source string into lines while tracking offset and line number.

        :yield: end offset of line, number of line (1-indexed), content of line
        :rtype: Tuple[int, int, str]
        """
        line_end_offset = 0
        for line_number, line in enumerate(self._source.split("\n"), start=1):
            line_end_offset += len(line)
            yield line_end_offset, line_number, line
            line_end_offset += 1  # Account for character lost to splitting.

    def _locate_in_line(self, offset: int) -> Tuple[int, str, int]:
        """Locate a desired offset within a line and provide details about the line.

        :param offset: target absolute offset
        :type offset: int
        :return: line number on which `offset` is found, content of line, relative offset of `offset` within the line
        :rtype: Tuple[int, str, int]
        """
        lines = self._source_as_lines()
        line_start_offset = 1
        line_end_offset = -1
        line_number = 1
        line = ""
        # Fetch the next line until the new line's end is ahead of the desired offset.
        # The fetched line thus contains the desired offset.
        while line_end_offset < offset:
            line_start_offset = line_end_offset + 2
            line_end_offset, line_number, line = next(lines)
        offset_from_line_start = offset - line_start_offset + 1  # Calculate the relative offset.
        return line_number, line, offset_from_line_start

    def _report(self, error_type: str, message: str, length: int, offset: int) -> None:
        """Output a formatted and underlined error and message to stderr."""
        line_number, line, line_offset = self._locate_in_line(offset)
        if self._debug_flags & Debug.REDUCED_ERROR_REPORTING:  # Better aligns with JLox output.
            if offset < len(self._source):
                lexeme = f"'{line[line_offset-length:line_offset]}'"
            else:
                lexeme = "end"
            eprint(f"[line {line_number}] {error_type} at {lexeme}: {message}")
        else:
            eprint(f"\n\t{line_number}{self.LINE_NUMBER_SEPARATOR}{line}")
            arrow_spacer = "\t" + " " * (
                len(str(line_number))
                + len(self.LINE_NUMBER_SEPARATOR)
                + (line_offset - length)
            )
            eprint(arrow_spacer + self.ERROR_MARKER * length)
            eprint(f"{error_type}: Line {line_number}: {message}")


class catch_internal_error:  # pylint: disable=invalid-name
    def __init__(self, *, dump_backtrace: bool, ignore_types: Tuple[Type[BaseException]]) -> None:
        self._dump_backtrace = dump_backtrace
        self._ignore_types = ignore_types

    def __enter__(self) -> None:
        return

    def __exit__(self, error_type: Type[BaseException], error: BaseException, tb) -> bool:  # type: ignore
        if error is not None:
            if isinstance(error, self._ignore_types):
                raise error
            if self._dump_backtrace:
                import traceback  # pylint: disable=import-outside-toplevel
                traceback.print_exception(error_type, error, tb)
                eprint("\nPylox crashed due to the internal error above.")
            else:
                eprint(
                    f"Pylox crashed due to an internal {error_type.__name__}.",
                    "For more information, run pylox with --dbg BACKTRACE.",
                    sep="\n"
                )
            raise LoxExit(1)
        return True
