from typing import List, Optional, Tuple, Union

from pylox.error import LoxErrorHandler, LoxSyntaxError
from pylox.streamview import StreamView
from pylox.token import COMPOUND_TOKENS, SINGLE_CHAR_TOKENS, LiteralValue, Token
from pylox.token import TokenType as TT
from pylox.utilities import dump_internal

# ~~~ helper functions ~~~


def _is_arabic_numeral(char: Optional[str]) -> bool:
    """Check if char is an Arabic numeral"""
    if char is None:
        return False
    return char in "1234567890"


def _is_valid_identifier_start(char: Optional[str]) -> bool:
    """Check if char is allowable as the first letter of an identifier"""
    if char is None:
        return False
    return char.isalpha() or char == "_"


def _is_valid_identifier_name(char: Optional[str]) -> bool:
    """Check if char can occur inside an identifier name"""
    if char is None:
        return False
    return _is_valid_identifier_start(char) or char.isdigit()


class Scanner:
    def __init__(
            self,
            source: str,
            error_handler: LoxErrorHandler,
            *,
            dump: bool = False
    ) -> None:
        """Scan a source string into Tokens """
        self._tokens: List[Token] = list()
        self._sv = StreamView(source)
        self._error_handler = error_handler
        self._dump = dump

    def scan_tokens(self) -> List[Token]:
        """Scan all tokens in the source stream"""
        while self._sv.has_next():
            # at the beginning of a lexeme
            self._sv.set_marker()
            self._scan_token()
        # mark the end of the stream
        self._sv.set_marker()
        self._add_token(TT.EOF)

        if self._dump:
            dump_internal("Token", *self._tokens)

        return self._tokens

    def _scan_token(self) -> None:
        """Scan the source stream for the next token and add it to the list"""
        char: str = self._sv.advance()
        next_token: Union[TT, Tuple[TT, LiteralValue], None] = None

        # match compound tokens before similar single-character versions
        if (doublet := char + str(self._sv.peek())) in COMPOUND_TOKENS:  # pylint: disable=superfluous-parens
            next_token = TT(doublet)
            self._sv.advance()
        elif char in SINGLE_CHAR_TOKENS:
            next_token = TT(char)
        elif char == "/":
            next_token = self._slash_helper()
        elif char == '"':
            next_token = self._string_helper()
        # whitespaces are dropped
        elif char.isspace():
            pass
        elif _is_arabic_numeral(char):
            next_token = self._number_helper()
        elif _is_valid_identifier_start(char):
            next_token = self._identifier_helper()
        # what remains is an error
        else:
            self._error_handler.err(LoxSyntaxError(self._sv.current_index, "Unexpected character"))

        if next_token:  # handle no-ops
            if isinstance(next_token, tuple):  # handle types that have literals
                self._add_token(*next_token)
            else:
                self._add_token(next_token)

    def _add_token(self, token_type: TT, literal: LiteralValue = None) -> None:
        """Add a new Token to the list using the passed type and optional literal value"""
        lexeme: str = self._sv.get_slice_from_marker()
        self._tokens.append(Token(token_type, lexeme, literal, self._sv.current_index))

    # ~~~ helpers for specific token types ~~~

    def _slash_helper(self) -> Optional[TT]:
        """Decide if the matched slash is division or a comment.
        Return a SLASH token or consume the comment."""
        if self._sv.advance_if_match("/"):
            # a comment takes up the entire line
            while self._sv.peek() != "\n" and self._sv.has_next():
                self._sv.advance()
            return None
        return TT.SLASH

    def _string_helper(self) -> Optional[Tuple[TT, str]]:
        """Consume an entire string"""
        while self._sv.peek() != '"' and self._sv.has_next():  # watch out for unterminated strings
            self._sv.advance()  # note that multi-line strings are allowed
        if not self._sv.has_next():  # unterminated string
            assert self._sv.marker_index is not None
            self._error_handler.err(
                LoxSyntaxError(
                    self._sv.current_index,
                    "Unterminated string",
                    length=self._sv.current_index - self._sv.marker_index
                )
            )
            return None
        # consume the closing double quotation mark
        self._sv.advance()
        # return the type and the the enclosed text
        assert self._sv.marker_index is not None
        return TT.STRING, self._sv[self._sv.marker_index + 1:self._sv.current_index - 1]

    def _number_helper(self) -> Tuple[TT, float]:
        """Consume an entire number"""
        while _is_arabic_numeral(self._sv.peek()):
            self._sv.advance()
        # consume a decimal point, if there is one
        # note that there must be another digit after the decimal
        # as in, "1234." is not a valid number
        if self._sv.peek() == "." and _is_arabic_numeral(self._sv.peek(1)):
            self._sv.advance()
            while _is_arabic_numeral(self._sv.peek()):  # consume any digits after the decimal point
                self._sv.advance()
        # parse the value of the number directly with Python
        return TT.NUMBER, float(self._sv.get_slice_from_marker())

    def _identifier_helper(self) -> TT:
        """Consume an entire identifier and decide if it is a keyword"""
        while _is_valid_identifier_name(self._sv.peek()):
            self._sv.advance()
        # add a keyword token if it is one, or an identifier otherwise
        name: str = self._sv.get_slice_from_marker()
        try:
            return TT(f"@{name.upper()}")  # keywords have enum values in the form "@KEYWORD"
        except ValueError:
            return TT.IDENTIFIER


__all__ = ("Scanner")
