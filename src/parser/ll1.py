from __future__ import annotations
from dataclasses import dataclass
from src.parser.grammar import Grammar, Symbol, Production, EPSILON_SYM
from src.parser.first_follow import compute_first, compute_follow, first_of_sequence


class LL1Error(Exception):
    pass


def build_ll1_table(grammar: Grammar) -> dict[tuple[str, str], Production]:
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table: dict[tuple[str, str], Production] = {}
    conflicts: list[str] = []

    for prod in grammar.productions:
        fa = first_of_sequence(prod.body, first)
        for sym in fa:
            if sym == EPSILON_SYM:
                continue
            key = (prod.head.name, sym.name)
            if key in table:
                conflicts.append(f"LL(1) conflict: M[{prod.head.name},{sym.name}]")
            table[key] = prod
        if EPSILON_SYM in fa:
            for sym in follow.get(prod.head, set()):
                key = (prod.head.name, sym.name)
                if key in table:
                    conflicts.append(f"LL(1) conflict: M[{prod.head.name},{sym.name}]")
                table[key] = prod

    if conflicts:
        raise LL1Error("; ".join(conflicts))

    return table


@dataclass
class LL1ParseStep:
    stack: list[str]
    remaining: list[str]
    action_taken: str


@dataclass
class LL1ParseResult:
    accepted: bool
    steps: list[LL1ParseStep]
    error: str | None = None


def ll1_parse(
    tokens: list[str],
    table: dict[tuple[str, str], Production],
    grammar: Grammar,
) -> LL1ParseResult:
    """tokens must end with '$'."""
    stack = ['$', str(grammar.start)]
    pos = 0
    steps: list[LL1ParseStep] = []

    while stack[-1] != '$':
        top = stack[-1]
        token = tokens[pos] if pos < len(tokens) else '$'

        if top == token:
            steps.append(LL1ParseStep(stack[:], tokens[pos:], f"match {token}"))
            stack.pop()
            pos += 1
        else:
            prod = table.get((top, token))
            if prod is None:
                expected = sorted({t for nt, t in table if nt == top})
                return LL1ParseResult(
                    accepted=False, steps=steps,
                    error=f"Unexpected '{token}' for '{top}'. Expected: {expected}",
                )
            steps.append(LL1ParseStep(stack[:], tokens[pos:], f"expand {prod}"))
            stack.pop()
            for sym in reversed(prod.body):
                if sym != EPSILON_SYM:
                    stack.append(sym.name)

    token = tokens[pos] if pos < len(tokens) else '$'
    if stack[-1] == '$' and token == '$':
        return LL1ParseResult(accepted=True, steps=steps)
    return LL1ParseResult(
        accepted=False, steps=steps,
        error=f"Incomplete parse. Stack: {stack}",
    )
