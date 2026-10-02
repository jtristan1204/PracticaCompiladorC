"""Analizador léxico de Mini C.

Se implementa en el **proyecto 1**. Aquí solo quedan el estado y las firmas;
cada método describe lo que debe hacer según el capítulo IV, §4.4.
"""

from minic.diagnostics import diagnostic_code
from minic.diagnostics.diagnostic_bag import DiagnosticBag
from minic.lexer.lexical_rules import (
    DOUBLE,
    KEYWORDS,
    NEWLINE,
    SINGLE,
    WHITESPACE,
    is_digit,
    is_identifier_part,
    is_identifier_start,
)
from minic.lexer.lexer_result import LexerResult
from minic.lexer.token import Token
from minic.lexer.token_type import TokenType


class Lexer:
    """Convierte el texto fuente en una lista de tokens.

    Uso: ``tokens, diagnostics = Lexer(source).scan()``.
    """

    def __init__(self, source: str) -> None:
        """Prepara el recorrido de ``source`` desde la línea 1, columna 1."""
        self._source = source
        self._start = 0
        self._current = 0
        self._line = 1
        self._column = 1
        self._start_line = 1
        self._start_column = 1
        self._tokens: list[Token] = []
        self._diagnostics = DiagnosticBag()

    def scan(self) -> LexerResult:
        """Recorre toda la fuente y devuelve los tokens y los diagnósticos.

        Mientras no se llegue al final: marca el inicio del lexema (índice,
        línea y columna) y llama a ``_scan_token``. Al terminar agrega
        exactamente un ``EOF`` con lexema vacío en la posición final.

        Devuelve:
            ``LexerResult(tokens, diagnostics)``.

        Referencia: capítulo IV, §4.4 (API y token ``EOF``).
        """
        while not self._is_at_end():
            self._start = self._current
            self._start_line = self._line
            self._start_column = self._column
            self._scan_token()

        self._start = self._current
        self._start_line = self._line
        self._start_column = self._column
        self._add_token(TokenType.EOF)

        return LexerResult(self._tokens, self._diagnostics.to_list())

    def _is_at_end(self) -> bool:
        """Indica si ya se consumió todo el texto fuente."""
        return self._current >= len(self._source)

    def _peek(self) -> str:
        """Devuelve el carácter actual sin consumirlo, o ``""`` al final."""
        if self._is_at_end():
            return ""
        return self._source[self._current]

    def _peek_next(self) -> str:
        """Devuelve el carácter siguiente al actual sin consumirlo, o ``""``."""
        if self._current + 1 >= len(self._source):
            return ""
        return self._source[self._current + 1]

    def _advance(self) -> str:
        """Consume y devuelve el carácter actual, actualizando la posición.

        Cada carácter suma una columna; ``\\n`` suma una línea y reinicia la
        columna en 1 (capítulo IV, §4.4, posiciones).
        """
        char = self._source[self._current]
        self._current += 1
        if char == NEWLINE:
            self._line += 1
            self._column = 1
        else:
            self._column += 1
        return char

    def _scan_token(self) -> None:
        """Reconoce un token a partir del carácter actual.

        Orden de decisión:
        1. Espacio en blanco (``WHITESPACE``): se consume sin producir token.
        2. Inicio de identificador: ``_scan_identifier``.
        3. Dígito: ``_scan_number``.
        4. Operador o símbolo: ``_scan_operator``.
        5. Cualquier otro carácter: ``_report_unrecognized``.
        """
        char = self._peek()

        if char in WHITESPACE:
            self._advance()
            return

        if is_identifier_start(char):
            self._scan_identifier()
            return

        if is_digit(char):
            self._scan_number()
            return

        if self._scan_operator():
            return

        self._report_unrecognized()

    def _scan_identifier(self) -> None:
        """Consume ``[A-Za-z_][A-Za-z0-9_]*`` y emite el token.

        Primero se consume el nombre completo y después se consulta
        ``KEYWORDS``: si está, el tipo es la reservada; si no, ``IDENTIFIER``.
        """
        while is_identifier_part(self._peek()):
            self._advance()

        text = self._source[self._start : self._current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _scan_number(self) -> None:
        """Consume ``[0-9]+`` y emite ``INTEGER_LITERAL`` con su valor en base 10.

        El valor va en ``literal`` como ``int`` sin cota (capítulo IV, §4.4).
        """
        while is_digit(self._peek()):
            self._advance()

        text = self._source[self._start : self._current]
        value = int(text)
        self._add_token(TokenType.INTEGER_LITERAL, literal=value)

    def _scan_operator(self) -> bool:
        """Intenta reconocer un operador o símbolo en la posición actual.

        Consulta ``DOUBLE`` antes que ``SINGLE`` (máxima coincidencia). Si
        reconoce algo, lo consume, emite el token y devuelve ``True``; si no,
        devuelve ``False`` sin consumir nada.
        """
        two = self._peek() + self._peek_next()
        if two in DOUBLE:
            self._advance()
            self._advance()
            self._add_token(DOUBLE[two])
            return True

        one = self._peek()
        if one in SINGLE:
            self._advance()
            self._add_token(SINGLE[one])
            return True

        return False

    def _add_token(self, token_type: str, literal: int | None = None) -> None:
        """Agrega un ``Token`` con el lexema entre el inicio marcado y la posición actual.

        La línea y la columna son las del **inicio** del lexema.
        """
        lexeme = self._source[self._start : self._current]
        self._tokens.append(
            Token(
                type=token_type,
                lexeme=lexeme,
                literal=literal,
                line=self._start_line,
                column=self._start_column,
            )
        )

    def _report_unrecognized(self) -> None:
        """Registra ``LEX001`` para el carácter actual, lo consume y continúa.

        Mensaje: ``Carácter no reconocido: '<c>'`` en la línea y la columna del
        carácter (``diagnostic_code.unrecognized_character``).
        """
        char = self._advance()
        self._diagnostics.report(
            diagnostic_code.LEX001,
            diagnostic_code.unrecognized_character(char),
            self._start_line,
            self._start_column,
        )
