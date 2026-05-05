from __future__ import annotations
from src.parser.grammar import Grammar, Symbol, EPSILON_SYM, EOF_SYM


def first_of_sequence(
    seq: tuple[Symbol, ...],
    first: dict[Symbol, set[Symbol]],
) -> set[Symbol]:
    result: set[Symbol] = set()
    for sym in seq:
        f = first.get(sym, set())
        result |= f - {EPSILON_SYM}
        if EPSILON_SYM not in f:
            return result
    result.add(EPSILON_SYM)
    return result


def compute_first(grammar: Grammar) -> dict[Symbol, set[Symbol]]:
    first: dict[Symbol, set[Symbol]] = {}
    for t in grammar.terminals:
        first[t] = {t}
    first[EPSILON_SYM] = {EPSILON_SYM}
    for nt in grammar.non_terminals:
        first[nt] = set()

    changed = True
    while changed:
        changed = False
        for prod in grammar.productions:
            head = prod.head
            old = len(first[head])
            if not prod.body:
                first[head].add(EPSILON_SYM)
            else:
                all_nullable = True
                for sym in prod.body:
                    f = first.get(sym, set())
                    first[head] |= f - {EPSILON_SYM}
                    if EPSILON_SYM not in f:
                        all_nullable = False
                        break
                if all_nullable:
                    first[head].add(EPSILON_SYM)
            if len(first[head]) > old:
                changed = True
    return first


def compute_follow(
    grammar: Grammar,
    first: dict[Symbol, set[Symbol]],
) -> dict[Symbol, set[Symbol]]:
    follow: dict[Symbol, set[Symbol]] = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start].add(EOF_SYM)

    changed = True
    while changed:
        changed = False
        for prod in grammar.productions:
            for i, sym in enumerate(prod.body):
                if sym.is_terminal:
                    continue
                if sym not in follow:
                    follow[sym] = set()
                old = len(follow[sym])
                beta = prod.body[i + 1:]
                first_beta = first_of_sequence(beta, first)
                follow[sym] |= first_beta - {EPSILON_SYM}
                if EPSILON_SYM in first_beta:
                    follow[sym] |= follow.get(prod.head, set())
                if len(follow[sym]) > old:
                    changed = True
    return follow
