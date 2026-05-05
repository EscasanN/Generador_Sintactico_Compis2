from __future__ import annotations
from dataclasses import dataclass
from src.parser.grammar import Grammar, Production
from src.parser.lr0 import LR0Automaton, build_lr0_automaton
from src.parser.slr1 import ParseTable, ParseResult, build_slr1_table, slr1_parse
from src.parser.lalr import build_lalr_table, lalr_parse
from src.parser.ll1 import build_ll1_table, ll1_parse, LL1ParseResult, LL1Error


@dataclass
class AnalysisResult:
    input_string: str
    tokens: list[str]
    slr1_result: ParseResult | None
    lalr_result: ParseResult | None
    ll1_result: LL1ParseResult | None
    ll1_error: str | None = None


class StringAnalyzer:
    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.automaton: LR0Automaton = build_lr0_automaton(grammar)
        self.slr1_table: ParseTable = build_slr1_table(self.automaton)
        self.lalr_table: ParseTable = build_lalr_table(grammar)

        self.ll1_table: dict[tuple[str, str], Production] | None = None
        self.ll1_error: str | None = None
        try:
            self.ll1_table = build_ll1_table(grammar)
        except LL1Error as e:
            self.ll1_error = str(e)

    def analyze(self, tokens: list[str]) -> AnalysisResult:
        tok_eof = tokens + ['$']
        slr1_r = slr1_parse(tok_eof, self.slr1_table)
        lalr_r = lalr_parse(tok_eof, self.lalr_table)
        ll1_r: LL1ParseResult | None = None
        if self.ll1_table is not None:
            ll1_r = ll1_parse(tok_eof, self.ll1_table, self.grammar)
        return AnalysisResult(
            input_string=' '.join(tokens),
            tokens=tokens,
            slr1_result=slr1_r,
            lalr_result=lalr_r,
            ll1_result=ll1_r,
            ll1_error=self.ll1_error,
        )
