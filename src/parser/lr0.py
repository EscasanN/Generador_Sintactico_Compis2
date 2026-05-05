from __future__ import annotations
from dataclasses import dataclass, field
from src.parser.grammar import Grammar, Symbol, Production


@dataclass(frozen=True)
class LR0Item:
    production: Production
    dot: int

    @property
    def at_end(self) -> bool:
        return self.dot >= len(self.production.body)

    @property
    def next_symbol(self) -> Symbol | None:
        if self.at_end:
            return None
        return self.production.body[self.dot]

    def advance(self) -> LR0Item:
        return LR0Item(self.production, self.dot + 1)

    def __repr__(self) -> str:
        body = list(self.production.body)
        before = ' '.join(str(s) for s in body[: self.dot])
        after = ' '.join(str(s) for s in body[self.dot:])
        if before and after:
            mid = f"{before} . {after}"
        elif after:
            mid = f". {after}"
        elif before:
            mid = f"{before} ."
        else:
            mid = "."
        return f"[{self.production.head} -> {mid}]"


def closure(items: frozenset[LR0Item], grammar: Grammar) -> frozenset[LR0Item]:
    result = set(items)
    changed = True
    while changed:
        changed = False
        for item in list(result):
            B = item.next_symbol
            if B is not None and not B.is_terminal:
                for prod in grammar.productions_for(B):
                    ni = LR0Item(prod, 0)
                    if ni not in result:
                        result.add(ni)
                        changed = True
    return frozenset(result)


def goto(items: frozenset[LR0Item], symbol: Symbol, grammar: Grammar) -> frozenset[LR0Item]:
    moved = frozenset(
        item.advance()
        for item in items
        if not item.at_end and item.next_symbol == symbol
    )
    return closure(moved, grammar) if moved else frozenset()


@dataclass
class LR0State:
    state_id: int
    items: frozenset[LR0Item]
    transitions: dict[Symbol, LR0State] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.state_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LR0State) and self.state_id == other.state_id

    def __repr__(self) -> str:
        return f"I{self.state_id}"


@dataclass
class LR0Automaton:
    states: list[LR0State]
    start: LR0State
    grammar: Grammar  # augmented grammar


class LR0Error(Exception):
    pass


def build_lr0_automaton(grammar: Grammar) -> LR0Automaton:
    aug = grammar.augmented()
    start_prod = aug.productions[0]
    init_items = closure(frozenset([LR0Item(start_prod, 0)]), aug)

    states: list[LR0State] = []
    items_to_state: dict[frozenset[LR0Item], LR0State] = {}

    def get_or_create(items: frozenset[LR0Item]) -> tuple[LR0State, bool]:
        if items in items_to_state:
            return items_to_state[items], False
        s = LR0State(len(states), items)
        states.append(s)
        items_to_state[items] = s
        return s, True

    start_state, _ = get_or_create(init_items)
    worklist = [start_state]

    while worklist:
        state = worklist.pop(0)
        next_symbols = {item.next_symbol for item in state.items if not item.at_end}
        for sym in next_symbols:
            goto_items = goto(state.items, sym, aug)
            if not goto_items:
                continue
            next_state, is_new = get_or_create(goto_items)
            state.transitions[sym] = next_state
            if is_new:
                worklist.append(next_state)

    return LR0Automaton(states=states, start=start_state, grammar=aug)
