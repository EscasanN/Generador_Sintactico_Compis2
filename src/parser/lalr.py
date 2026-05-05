from __future__ import annotations
from dataclasses import dataclass
from src.parser.grammar import Grammar, Symbol, Production, EPSILON_SYM, EOF_SYM
from src.parser.first_follow import compute_first, first_of_sequence
from src.parser.slr1 import ParseTable, ParseResult, slr1_parse


@dataclass(frozen=True)
class LR1Item:
    production: Production
    dot: int
    lookahead: Symbol

    @property
    def at_end(self) -> bool:
        return self.dot >= len(self.production.body)

    @property
    def next_symbol(self) -> Symbol | None:
        return None if self.at_end else self.production.body[self.dot]

    def advance(self) -> LR1Item:
        return LR1Item(self.production, self.dot + 1, self.lookahead)

    @property
    def lr0_core(self) -> tuple[Production, int]:
        return (self.production, self.dot)


def _lr1_closure(
    items: frozenset[LR1Item],
    grammar: Grammar,
    first: dict[Symbol, set[Symbol]],
) -> frozenset[LR1Item]:
    result = set(items)
    changed = True
    while changed:
        changed = False
        for item in list(result):
            B = item.next_symbol
            if B is None or B.is_terminal:
                continue
            beta_la = item.production.body[item.dot + 1:] + (item.lookahead,)
            fs = first_of_sequence(beta_la, first) - {EPSILON_SYM}
            for prod in grammar.productions_for(B):
                for la in fs:
                    ni = LR1Item(prod, 0, la)
                    if ni not in result:
                        result.add(ni)
                        changed = True
    return frozenset(result)


def _lr1_goto(
    items: frozenset[LR1Item],
    symbol: Symbol,
    grammar: Grammar,
    first: dict[Symbol, set[Symbol]],
) -> frozenset[LR1Item]:
    moved = frozenset(
        item.advance()
        for item in items
        if not item.at_end and item.next_symbol == symbol
    )
    return _lr1_closure(moved, grammar, first) if moved else frozenset()


def build_lalr_table(grammar: Grammar) -> ParseTable:
    aug = grammar.augmented()
    first = compute_first(aug)
    start_prod = aug.productions[0]
    init = _lr1_closure(frozenset([LR1Item(start_prod, 0, EOF_SYM)]), aug, first)

    lr1_states: list[frozenset[LR1Item]] = []
    state_idx: dict[frozenset[LR1Item], int] = {}
    transitions: dict[tuple[int, Symbol], int] = {}

    def get_or_add(s: frozenset[LR1Item]) -> tuple[int, bool]:
        if s in state_idx:
            return state_idx[s], False
        i = len(lr1_states)
        lr1_states.append(s)
        state_idx[s] = i
        return i, True

    get_or_add(init)
    worklist = [0]
    while worklist:
        si = worklist.pop(0)
        st = lr1_states[si]
        syms = {item.next_symbol for item in st if not item.at_end}
        for sym in syms:
            g2 = _lr1_goto(st, sym, aug, first)
            if not g2:
                continue
            ni, is_new = get_or_add(g2)
            transitions[(si, sym)] = ni
            if is_new:
                worklist.append(ni)

    # Merge by LR(0) core → LALR
    core_to_ids: dict[frozenset[tuple[Production, int]], list[int]] = {}
    for i, st in enumerate(lr1_states):
        core = frozenset(item.lr0_core for item in st)
        core_to_ids.setdefault(core, []).append(i)

    lr1_to_lalr: dict[int, int] = {}
    lalr_counter = 0
    for ids in core_to_ids.values():
        for i in ids:
            lr1_to_lalr[i] = lalr_counter
        lalr_counter += 1

    action: dict[tuple[int, str], tuple[str, int]] = {}
    goto_table: dict[tuple[int, str], int] = {}
    conflicts: list[str] = []

    for lr1_id, st in enumerate(lr1_states):
        lalr_id = lr1_to_lalr[lr1_id]
        for item in st:
            if not item.at_end:
                sym = item.next_symbol
                if sym is not None and sym.is_terminal:
                    lr1_ns = transitions.get((lr1_id, sym))
                    if lr1_ns is not None:
                        key = (lalr_id, sym.name)
                        na: tuple[str, int] = ('shift', lr1_to_lalr[lr1_ns])
                        if key in action and action[key] != na:
                            conflicts.append(f"LALR S/R at {lalr_id} on '{sym.name}'")
                        action[key] = na
            else:
                prod = item.production
                if prod == start_prod:
                    action[(lalr_id, '$')] = ('accept', 0)
                else:
                    key = (lalr_id, item.lookahead.name)
                    na = ('reduce', prod.index)
                    if key in action and action[key] != na:
                        conflicts.append(f"LALR R/R at {lalr_id} on '{item.lookahead.name}'")
                    else:
                        action[key] = na

    for (lr1_id, sym), lr1_ns in transitions.items():
        if not sym.is_terminal:
            goto_table[(lr1_to_lalr[lr1_id], sym.name)] = lr1_to_lalr[lr1_ns]

    return ParseTable(action=action, goto_table=goto_table, conflicts=conflicts, grammar=aug)


def lalr_parse(tokens: list[str], table: ParseTable) -> ParseResult:
    return slr1_parse(tokens, table)
