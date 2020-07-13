from typing import List, Optional, Tuple, Union

from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.lox_types import LoxLiteral, lox_is_valid_identifier_name, lox_is_valid_identifier_start
from pylox.streamview import StreamView
from pylox.token import COMPOUND_TOKENS, SINGLE_CHAR_TOKENS, Tk, Token
from pylox.utilities import Debug, is_arabic_numeral, dump_internal


class Scanner:
    def __init__(
            self,
            source: str,
            error_handler: LoxErrorHandler,
            *,
            debug_flags: Debug
    ) -> None:
        """Produce a list of Tokens from a source string.

        :param source: source string
        :type source: str
        :param error_handler: error reporting manager
        :type error_handler: LoxErrorHandler
        :param dump: whether to dump tokens, defaults to False
        :type dump: bool, optional
        """
        self._tokens: List[Token] = list()
        self._sv = StreamView(source)
        self._error_handler = error_handler
        self._debug_flags = debug_flags

    def scan_tokens(self) -> List[Token]:
        """Scan all tokens in the source stream."""
        while self._sv.has_next():
            # At the beginning of a lexeme.
            self._sv.set_marker()
            self._scan_token()
        self._add_token(Tk.EOF)

        if self._debug_flags & Debug.DUMP_TOKENS:
            if self._debug_flags & Debug.JAVA_STYLE_TOKENS:  # Replicate JLox output.
                print(*(token.to_string() for token in self._tokens), sep="\n")
            else:
                dump_internal("Token", *self._tokens)

        return self._tokens

    def _scan_token(self) -> None:
        """Scan the source stream for the next token and add it to the list"""
        char = self._sv.advance()
        next_token: Union[Tk, Tuple[Tk, LoxLiteral], None] = None

        # Match compound tokens before similar single-character versions.
        if (doublet := char + str(self._sv.peek())) in COMPOUND_TOKENS:  # pylint: disable=superfluous-parens
            next_token = Tk(doublet)
            self._sv.advance()
        elif char in SINGLE_CHAR_TOKENS:
            next_token = Tk(char)
        elif char == "/":
            next_token = self._slash()
        elif char == '"':
            next_token = self._string()
        elif char.isspace():  # Whitespaces are dropped.
            pass
        elif is_arabic_numeral(char):
            next_token = self._number()
        elif lox_is_valid_identifier_start(char):
            next_token = self._identifier()
        else:  # What remains is an error.
            self._error_handler.err(LoxSyntaxError(self._sv.current_index, "Unexpected character."))

        if next_token:  # Handle no-ops.
            if isinstance(next_token, tuple):  # Handle types that have literals.
                self._add_token(*next_token)
            else:
                self._add_token(next_token)

    def _add_token(self, token_type: Tk, literal: Optional[LoxLiteral] = None) -> None:
        """Add a new Token to the list using the passed type and optional literal value"""
        if token_type is Tk.EOF:  # EOF must be populated manually.
            lexeme = "\0"
            offset = self._sv.current_index + 1
        else:
            lexeme = self._sv.get_slice_from_marker()
            offset = self._sv.current_index
        self._tokens.append(Token(token_type, lexeme, literal, offset))

    # ~~~ Helpers for specific token types ~~~

    def _slash(self) -> Optional[Tk]:
        """Decide if the matched slash is division or a comment.
        Return a SLASH token or consume the comment."""
        if self._sv.advance_if_match("/"):  # A comment must be followed by another slash.
            while self._sv.peek() != "\n" and self._sv.has_next():  # A comment takes up the entire line.
                self._sv.advance()
            return None  # No token to be produced this pass.
        return Tk.SLASH

    def _string(self) -> Optional[Tuple[Tk, str]]:
        """Consume an entire string."""
        while self._sv.peek() != '"' and self._sv.has_next():  # Test for unterminated string.
            self._sv.advance()  # Note that multi-line strings are allowed.
        if not self._sv.has_next():  # Error on unterminated string.
            assert self._sv.marker_index is not None  # Make mypy happy.
            self._error_handler.err(LoxSyntaxError(
                self._sv.current_index,
                "Unterminated string.",
                length=self._sv.current_index - self._sv.marker_index
            ))
            return None
        # Consume the closing double quotation mark.
        self._sv.advance()
        # Return the type and the the enclosed text, stripping the quotation marks.
        assert self._sv.marker_index is not None
        return Tk.STRING, self._sv[self._sv.marker_index + 1:self._sv.current_index - 1]

    def _number(self) -> Tuple[Tk, float]:
        """Consume an entire number."""
        while is_arabic_numeral(self._sv.peek()):
            self._sv.advance()
        # Consume a decimal point, if there is one. Note that there must be another
        # digit after the decimal: as in, "1234." is not a valid number.
        if self._sv.peek() == "." and is_arabic_numeral(self._sv.peek(1)):
            self._sv.advance()
            while is_arabic_numeral(self._sv.peek()):  # Consume any digits after the decimal point.
                self._sv.advance()
        # Parse the value of the number directly with Python.
        return Tk.NUMBER, float(self._sv.get_slice_from_marker())

    def _identifier(self) -> Tk:
        """Consume an entire identifier and decide if it is a keyword."""
        while lox_is_valid_identifier_name(self._sv.peek()):
            self._sv.advance()
        # Add a keyword token if it is one, or an identifier otherwise.
        name = self._sv.get_slice_from_marker()
        try:
            return Tk(f"@{name.upper()}")  # Keywords have enum values in the form "@KEYWORD".
        except ValueError:
            return Tk.IDENTIFIER
