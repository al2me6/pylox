"""test.py

Test suite for Pylox.

Parts of this code are adapted from
https://github.com/munificent/craftinginterpreters/blob/93e3f56e3cfd78a9facc747b3ec6e5022ae7f4bc/util/test.py
by Bob Nystrom, licensed MIT.

As such, this file is distributed under the MIT license.
"""

import os
import re
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout, suppress
from io import StringIO
from operator import eq
from pathlib import Path
from typing import Collection, Iterable, List, Optional, Sequence, TypeVar

from pylox.lox import Lox
from pylox.utilities import indent
from pylox.utilities.configuration import Debug
from pylox.utilities.error import LoxExit

T = TypeVar("T")


def compare_inner(left: Collection[T], right: Collection[T]) -> bool:
    if len(left) != len(right):
        return False
    return all(map(eq, left, right))


def red(string: str) -> str:
    return f"\033[31m{string}\033[0m"


def green(string: str) -> str:
    return f"\033[32m{string}\033[0m"


OUTPUT_EXPECT = re.compile(r'// expect: ?(.*)')
ERROR_EXPECT = re.compile(r'// Error at ((end|\'[^\']+\')(.*))')
ERROR_LINE_EXPECT = re.compile(r'// \[(java )?line (\d+)\] Error at ((end|\'[^\']+\')(.*))')
RUNTIME_ERROR_EXPECT = re.compile(r'// expect runtime error: (.+)')

OUT_ERROR_PARSER = re.compile(r'\[line (\d+)\] (LoxSyntaxError|LoxRuntimeError)( at .*):(.*)')


class Test:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._expected_output: List[str] = list()
        self._expected_errors: List[str] = list()

    def execute(self, lox_instance: Lox, out_buf: StringIO) -> bool:
        lox_instance.interpreter.reinitialize_environment()

        out_capture = StringIO()
        err_capture = StringIO()
        with self.path.open("r") as fil:
            source = fil.read()

        self._compute_expected_output(source)

        with suppress(LoxExit), redirect_stderr(err_capture), redirect_stdout(out_capture):
            lox_instance.run(source)

        out = tuple(line.strip() for line in out_capture.getvalue().splitlines())
        err = tuple(line.strip() for line in err_capture.getvalue().splitlines())

        if not (message := self._verify(out, err)):
            print(f"[{green('PASS')}]: {self.path}", file=out_buf)
            return True
        else:
            print(f"[{red('FAIL')}]: {self.path}", file=out_buf)
            print(indent(message), file=out_buf)
            return False

    def _compute_expected_output(self, source: str) -> None:
        # TODO: fix this string manipulation madness.
        # TODO: support "Error at "symbol" expectations.
        expect_runtime_error = list()
        for line_number, line in enumerate(source.splitlines(), start=1):
            if match := OUTPUT_EXPECT.search(line):
                self._expected_output.append(match.group(1))
            if match := ERROR_EXPECT.search(line):
                self._expected_errors.append(f"[line {line_number}] LoxSyntaxError at {match.group(1)}")
            if match := ERROR_LINE_EXPECT.search(line):
                self._expected_errors.append(f"[line {match.group(2)}] LoxSyntaxError at {match.group(3)}")
            if match := RUNTIME_ERROR_EXPECT.search(line):
                if self._expected_errors:
                    raise RuntimeError("Cannot have both compile- and runtime errors.")
                expect_runtime_error.append(f"[line {line_number}] LoxRuntimeError: {match.group(1)}")
        self._expected_errors.extend(expect_runtime_error)

    def _verify(self, output: Sequence[str], errors: Sequence[str]) -> Optional[str]:
        error_message = "Expect:\n{}Encountered:\n{}\n"
        errors = tuple(map(self._reformat_pylox_error, errors))
        if not compare_inner(errors, self._expected_errors):
            return error_message.format(indent(*self._expected_errors), indent(*errors))
        if not compare_inner(output, self._expected_output):
            return error_message.format(indent(*self._expected_output), indent(*output))
        return None

    def _reformat_pylox_error(self, err: str) -> str:
        if match := OUT_ERROR_PARSER.search(err):
            if match.group(2) == "LoxRuntimeError":
                return f"[line {match.group(1)}] LoxRuntimeError:{match.group(4)}"
            return err
        raise RuntimeError(f"Unexpected error output format: {err}")


class Tester:
    TEST_PATHS = (
        "assignment",
        "block",
        "bool",
        "call",
        "class",
        "closure",
        "comments",
        "constructor",
        "field",
        "for",
        "function",
        "if",
        "logical_operator",
        "nil",
        "number",
        "operator",
        "print",
        "string",
        "this",
        "variable",
        "while",
        "empty_file.lox",
        "precedence.lox",
        "unexpected_character.lox",
        "../test_suite_extensions",
    )

    IGNORED_PATHS = (
        "function/print.lox",  # No `clock()` function yet.
        "function/too_many_arguments.lox",  # Arbitrary restrictions are not implemented.
        "function/too_many_parameters.lox",  # Arbitrary restrictions are not implemented.
    )

    def __init__(self) -> None:
        self._queued_tests: List[Test] = list()
        self._lox_instance = Lox(Debug.JAVA_STYLE_TOKENS | Debug.REDUCED_ERROR_REPORTING)
        self._fails_output = StringIO()

        self._test_root = Path(os.path.realpath(__file__)).parent.parent / "test_suite"
        if not self._test_root.is_dir():
            raise FileNotFoundError("Test suite not found!")
        print(f"Test suite discovered at '{self._test_root}'.")

        ignored_paths_full = tuple(self._test_root / path for path in self.IGNORED_PATHS)

        for path in self.TEST_PATHS:
            self._discover_and_queue_tests(self._test_root / path, ignored_paths_full)
        print(f"{len(self._queued_tests)} tests found.")

    def test(self) -> None:
        errors = 0

        print("Executing tests...\n")
        test_count = len(self._queued_tests)
        test_count_str_len = len(str(test_count))

        for num, test in enumerate(self._queued_tests, start=1):
            out_buf = StringIO()
            print(f"{num:>{test_count_str_len}}/{test_count} ", end="", file=out_buf)
            result = test.execute(self._lox_instance, out_buf)
            print(out_buf.getvalue().rstrip())
            if not result:
                errors += 1
                print(f"{out_buf.getvalue().rstrip()}\n", file=self._fails_output)

        if errors:
            print(f"\nThe following tests {red('failed')}:\n\n{self._fails_output.getvalue()}", end="")
            print(
                f"{errors} tests {red('failed')}, "
                f"{test_count-errors} tests {green('passed')}."
            )
            sys.exit(1)
        else:
            print(f"\nAll {test_count} tests {green('passed')}!")
            sys.exit()

    @contextmanager
    def _apply_special_options(self, *options: Debug):  # type: ignore
        for option in options:
            self._lox_instance.debug_flags |= option
        yield
        for option in options:
            self._lox_instance.debug_flags ^= option

    def _discover_and_queue_tests(self, path: Path, ignored: Iterable[Path]) -> None:
        assert path.exists()
        if path.is_dir():
            for sub_path in sorted(path.iterdir()):
                self._discover_and_queue_tests(path / sub_path, ignored)
        else:  # Is file.
            if path not in ignored:
                self._queued_tests.append(Test(path))
