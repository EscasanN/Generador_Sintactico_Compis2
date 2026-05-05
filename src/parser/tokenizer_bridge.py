"""Run YALex pipeline on a .yal file and tokenize an input string."""
from __future__ import annotations
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.lexer.scanner import Scanner
from src.lexer.regex_parser import YALexParser
from src.lexer.resolver import DefinitionResolver
from src.lexer.nfa import build_nfa
from src.lexer.dfa import build_dfa, minimize_dfa


def tokenize_input(
    yalex_path: str,
    input_text: str,
    skip_tokens: set[str] | None = None,
) -> list[str]:
    """Return list of token type names from input_text using the .yal lexer."""
    if skip_tokens is None:
        skip_tokens = {'WHITESPACE'}

    scanner_result = Scanner(yalex_path).process()
    lexer_spec = YALexParser(scanner_result).parse()
    resolved = DefinitionResolver(lexer_spec).resolve()
    nfa = build_nfa(resolved)
    dfa = build_dfa(nfa)
    min_dfa = minimize_dfa(dfa)

    tokens: list[str] = []
    pos = 0
    while pos < len(input_text):
        state = min_dfa.start
        last_accept: tuple[str, int] | None = None
        cur = pos

        while cur < len(input_text):
            ch = ord(input_text[cur])
            next_state = state.transitions.get(ch)
            if next_state is None:
                break
            state = next_state
            cur += 1
            if state.is_accept and state.token:
                last_accept = (_extract_token_name(state.token), cur)

        if last_accept is None:
            raise ValueError(
                f"Lexer error at position {pos}: unexpected '{input_text[pos]}'"
            )
        name, end_pos = last_accept
        if name not in skip_tokens:
            tokens.append(name)
        pos = end_pos

    return tokens


def _extract_token_name(action: str) -> str:
    m = re.search(r'return\s+(\w+)', action)
    return m.group(1) if m else action.strip().strip('{}').strip()
