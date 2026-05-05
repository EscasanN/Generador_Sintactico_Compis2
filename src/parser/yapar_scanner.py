from __future__ import annotations
import re
from dataclasses import dataclass
from src.parser.grammar import Grammar, Symbol, Production, GrammarError, EOF_SYM


@dataclass
class YAParSpec:
    tokens: list[str]
    ignore_tokens: list[str]
    start_symbol: str
    raw_productions: list[tuple[str, list[list[str]]]]


class YAParScannerError(Exception):
    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.line = line


class YAParScanner:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def scan(self) -> YAParSpec:
        with open(self.filepath, encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'//[^\n]*', '', content)

        sections = content.split('%%')
        if len(sections) < 2:
            raise YAParScannerError("Missing %% separator in .yapar file")

        header, rules_section = sections[0], sections[1]
        tokens: list[str] = []
        ignore_tokens: list[str] = []
        start_symbol: str | None = None

        for line in header.splitlines():
            line = line.strip()
            if line.startswith('%token'):
                tokens.extend(line[6:].split())
            elif line.startswith('%start'):
                parts = line[6:].split()
                if parts:
                    start_symbol = parts[0]
            elif line.upper().startswith('IGNORE'):
                ignore_tokens.extend(line.split()[1:])

        if not tokens:
            raise YAParScannerError("No %token declarations found")
        if not start_symbol:
            # infer from first production head
            for block in rules_section.split(';'):
                block = block.strip()
                if not block:
                    continue
                colon_idx = block.find(':')
                if colon_idx != -1:
                    start_symbol = block[:colon_idx].strip()
                    break
        if not start_symbol:
            raise YAParScannerError("No %start declaration found and no productions")

        raw_productions: list[tuple[str, list[list[str]]]] = []
        for block in rules_section.split(';'):
            block = block.strip()
            if not block:
                continue
            colon_idx = block.find(':')
            if colon_idx == -1:
                continue
            head = block[:colon_idx].strip()
            alts_str = block[colon_idx + 1:]
            alternatives: list[list[str]] = []
            for alt in alts_str.split('|'):
                syms = alt.split()
                alternatives.append([] if not syms else syms)
            if head and alternatives:
                raw_productions.append((head, alternatives))

        if not raw_productions:
            raise YAParScannerError("No grammar rules found")

        return YAParSpec(
            tokens=tokens,
            ignore_tokens=ignore_tokens,
            start_symbol=start_symbol,
            raw_productions=raw_productions,
        )


def build_grammar(spec: YAParSpec) -> Grammar:
    terminal_names = set(spec.tokens) | {'$'}
    nt_names = {head for head, _ in spec.raw_productions}

    def make_sym(name: str) -> Symbol:
        if name in terminal_names:
            return Symbol(name, True)
        if name in nt_names:
            return Symbol(name, False)
        raise GrammarError(f"Undefined symbol: '{name}'")

    productions: list[Production] = []
    idx = 0
    for head_name, alternatives in spec.raw_productions:
        head = Symbol(head_name, False)
        for alt in alternatives:
            body = tuple(make_sym(s) for s in alt)
            productions.append(Production(head, body, idx))
            idx += 1

    start = Symbol(spec.start_symbol, False)
    if spec.start_symbol not in nt_names:
        raise GrammarError(f"Start symbol '{spec.start_symbol}' not defined")

    return Grammar(
        terminals=frozenset(Symbol(t, True) for t in terminal_names),
        non_terminals=frozenset(Symbol(nt, False) for nt in nt_names),
        productions=productions,
        start=start,
    )
