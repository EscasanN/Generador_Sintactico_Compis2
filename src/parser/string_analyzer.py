from __future__ import annotations
import re
from dataclasses import dataclass, field
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
    token_spans: list[tuple[int, int]] = field(default_factory=list)


def _enrich_lr_error(
    result: ParseResult,
    spans: list[tuple[int, int]],
    input_text: str,
) -> ParseResult:
    if result.accepted or not result.error:
        return result
    m = re.search(r'at position (\d+)', result.error)
    if not m:
        return result
    idx = int(m.group(1))
    if idx < len(spans):
        start, end = spans[idx]
        near = input_text[start:end]
        enriched = result.error + f"  →  column {start + 1}, near '{near}'"
    elif idx == len(spans):
        enriched = result.error + f"  →  end of input"
    else:
        return result
    return ParseResult(accepted=False, steps=result.steps, error=enriched, tree=result.tree)


def _enrich_ll1_error(
    result: LL1ParseResult,
    spans: list[tuple[int, int]],
    input_text: str,
) -> LL1ParseResult:
    if result.accepted or not result.error:
        return result
    # LL1 error mentions the token name; find it in the steps to estimate position
    step_count = len(result.steps)
    # count match steps to approximate consumed tokens
    consumed = sum(1 for s in result.steps if s.action_taken.startswith('match'))
    idx = consumed
    if idx < len(spans):
        start, end = spans[idx]
        near = input_text[start:end]
        enriched = result.error + f"  →  column {start + 1}, near '{near}'"
    elif idx == len(spans):
        enriched = result.error + f"  →  end of input"
    else:
        return result
    return LL1ParseResult(accepted=False, steps=result.steps, error=enriched, tree=result.tree)


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

    def analyze(
        self,
        tokens: list[str],
        spans: list[tuple[int, int]] | None = None,
        input_text: str = '',
    ) -> AnalysisResult:
        tok_eof = tokens + ['$']
        slr1_r = slr1_parse(tok_eof, self.slr1_table)
        lalr_r = lalr_parse(tok_eof, self.lalr_table)
        ll1_r: LL1ParseResult | None = None
        if self.ll1_table is not None:
            ll1_r = ll1_parse(tok_eof, self.ll1_table, self.grammar)

        if spans and input_text:
            slr1_r = _enrich_lr_error(slr1_r, spans, input_text)
            lalr_r = _enrich_lr_error(lalr_r, spans, input_text)
            if ll1_r is not None:
                ll1_r = _enrich_ll1_error(ll1_r, spans, input_text)

        return AnalysisResult(
            input_string=input_text or ' '.join(tokens),
            tokens=tokens,
            slr1_result=slr1_r,
            lalr_result=lalr_r,
            ll1_result=ll1_r,
            ll1_error=self.ll1_error,
            token_spans=spans or [],
        )
