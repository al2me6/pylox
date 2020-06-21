"""test.py

Test suite for Pylox.

Parts of this code are adapted from
https://github.com/munificent/craftinginterpreters/blob/93e3f56e3cfd78a9facc747b3ec6e5022ae7f4bc/util/test.py
by Bob Nystrom, licensed MIT.
"""

import io
import os
import re
import sys
from contextlib import redirect_stderr, redirect_stdout, suppress
from operator import eq
from pathlib import Path
from typing import Collection, List, Optional, Sequence, Set

from termcolor import colored

from ..error import LoxExit
from ..lox import Lox
from ..utilities import Debug


def indent(*block: str) -> str:
    return "\n".join(f"\t{line}" for blk in block for line in blk.splitlines())


def compare_inner(left: Collection, right: Collection) -> bool:
    if len(left) != len(right):
        return False
    return all(map(eq, left, right))


OUTPUT_EXPECT = re.compile(r'// expect: ?(.*)')
ERROR_EXPECT = re.compile(r'// Error( at (end|\'[^\']+\'))?(.*)')
ERROR_LINE_EXPECT = re.compile(r'// \[line (\d+)\] Error( at (end|\'[^\']+\'))?(.*)')
RUNTIME_ERROR_EXPECT = re.compile(r'// expect runtime error: (.+)')

OUT_ERROR_PARSER = re.compile(r'\[line (\d+)\] ((LoxSyntaxError|LoxRuntimeError).*)')


class Test:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._expected_output: List[str] = list()
        self._expected_errors: Set[str] = set()

    def execute(self, lox_instance: Lox) -> bool:
        out_capture = io.StringIO()
        err_capture = io.StringIO()
        with self.path.open("r") as fil:
            source = fil.read()

        self._compute_expected_output(source)

        with suppress(LoxExit), redirect_stderr(err_capture), redirect_stdout(out_capture):
            lox_instance.run(source)

        out = tuple(line.strip() for line in out_capture.getvalue().splitlines())
        err = tuple(line.strip() for line in err_capture.getvalue().splitlines())

        if not (message := self._verify(out, err)):
            print(f"[{colored('PASS', 'green')}]: {self.path}")
            return True
        else:
            print(f"[{colored('FAIL', 'red')}]: {self.path}")
            print(indent(message))
            return False

    def _compute_expected_output(self, source: str) -> None:
        # TODO: fix this string manipulation madness.
        # TODO: support "Error at "symbol" expectations.
        expect_runtime_error = set()
        for line_number, line in enumerate(source.splitlines(), start=1):
            if (match := OUTPUT_EXPECT.search(line)):
                self._expected_output.append(match.group(1))
            if (match := ERROR_EXPECT.search(line)):
                self._expected_errors.add(f"[line {line_number}] LoxSyntaxError{match.group(3)}")
            if (match := ERROR_LINE_EXPECT.search(line)):
                self._expected_errors.add(f"[line {match.group(1)}] LoxSyntaxError{match.group(4)}")
            if (match := RUNTIME_ERROR_EXPECT.search(line)):
                if self._expected_errors:
                    raise RuntimeError("Cannot have both compile- and runtime errors.")
                expect_runtime_error.add(f"[line {line_number}] LoxRuntimeError: {match.group(1)}")
        self._expected_errors.update(expect_runtime_error)

    def _verify(self, output: Sequence[str], errors: Sequence[str]) -> Optional[str]:
        error_message = "Expect:\n{}\nEncountered:\n{}\n"
        if not compare_inner(errors, self._expected_errors):
            return error_message.format(indent(*self._expected_errors), indent(*errors))
        if not compare_inner(output, self._expected_output):
            return error_message.format(indent(*self._expected_output), indent(*output))
        return None


class Tester:
    TEST_PATHS = (
        "assignment",
        "block",
        "bool",
        "comments",
        "nil",
        "number",
        "operator",
        "print",
        "string",
        "variable",
        "empty_file.lox",
        "precedence.lox",
        "unexpected_character.lox",
    )

    def __init__(self) -> None:
        self._queued_tests: List[Test] = list()
        self._lox_instance = Lox(Debug.JAVA_STYLE_TOKENS | Debug.REDUCED_ERROR_REPORTING)

        self._test_root = Path(os.path.realpath(__file__)).parent.parent.parent / "test_suite"
        if not self._test_root.is_dir():
            raise FileNotFoundError("Test suite not found!")
        print(f"Test suite discovered at '{self._test_root}'.")

        for path in self.TEST_PATHS:
            self._discover_and_queue_tests(self._test_root / path)
        print(f"{len(self._queued_tests)} tests found.")

    def test(self) -> None:
        errors = 0

        print("Executing tests...\n")
        test_count = len(self._queued_tests)
        test_count_str_len = len(str(test_count))

        for num, test in enumerate(self._queued_tests, start=1):
            print(f"{num:>{f'{test_count_str_len}'}}/{test_count} ", end="")
            if not test.execute(self._lox_instance):
                errors += 1

        print()
        if errors:
            print(
                f"{errors} tests {colored('failed', 'red')}, "
                f"{test_count-errors} tests {colored('passed', 'green')}."
            )
            sys.exit(1)
        else:
            print(f"All {test_count} tests {colored('passed', 'green')}!")
            sys.exit()

    def _discover_and_queue_tests(self, path: Path) -> None:
        assert path.exists()
        if path.is_dir():
            for sub_path in path.iterdir():
                self._discover_and_queue_tests(path / sub_path)
        else:  # Is file.
            self._queued_tests.append(Test(path))