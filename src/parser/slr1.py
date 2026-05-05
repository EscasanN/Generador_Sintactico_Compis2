from __future__ import annotations
from dataclasses import dataclass
from src.parser.grammar import Grammar, Symbol
from src.parser.lr0 import LR0Automaton
from src.parser.first_follow import compute_first, compute_follow


@dataclass
class ParseTable:
    action: dict[tuple[int, str], tuple[str, int]]
    goto_table: dict[tuple[int, str], int]
    conflicts: list[str]
    grammar: Grammar

    def has_conflicts(self) -> bool:
        return bool(self.conflicts)


@dataclass
class ParseStep:
    stack: list[int]
    symbols: list[str]
    remaining: list[str]
    action_taken: str


@dataclass
class ParseResult:
    accepted: bool
    steps: list[ParseStep]
    error: str | None = None


def build_slr1_table(automaton: LR0Automaton) -> ParseTable:
    aug = automaton.grammar
    first = compute_first(aug)
    follow = compute_follow(aug, first)
    aug_start = aug.productions[0]

    action: dict[tuple[int, str], tuple[str, int]] = {}
    goto_table: dict[tuple[int, str], int] = {}
    conflicts: list[str] = []

    for state in automaton.states:
        for item in state.items:
            if not item.at_end:
                sym = item.next_symbol
                if sym is not None and sym.is_terminal:
                    ns = state.transitions.get(sym)
                    if ns:
                        key = (state.state_id, sym.name)
                        new_act: tuple[str, int] = ('shift', ns.state_id)
                        if key in action and action[key] != new_act:
                            conflicts.append(
                                f"S/R conflict at I{state.state_id} on '{sym.name}'"
                            )
                        action[key] = new_act
            else:
                prod = item.production
                if prod == aug_start:
                    action[(state.state_id, '$')] = ('accept', 0)
                else:
                    for t in follow.get(prod.head, set()):
                        key = (state.state_id, t.name)
                        new_act = ('reduce', prod.index)
                        if key in action and action[key] != new_act:
                            conflicts.append(
                                f"Conflict at I{state.state_id} on '{t.name}'"
                            )
                        else:
                            action[key] = new_act

        for sym, ns in state.transitions.items():
            if not sym.is_terminal:
                goto_table[(state.state_id, sym.name)] = ns.state_id

    return ParseTable(action=action, goto_table=goto_table, conflicts=conflicts, grammar=aug)


def slr1_parse(tokens: list[str], table: ParseTable) -> ParseResult:
    """tokens must end with '$'."""
    stack = [0]
    symbols: list[str] = []
    steps: list[ParseStep] = []
    pos = 0

    while True:
        state = stack[-1]
        token = tokens[pos] if pos < len(tokens) else '$'
        act = table.action.get((state, token))

        if act is None:
            expected = sorted({t for s, t in table.action if s == state})
            return ParseResult(
                accepted=False,
                steps=steps,
                error=f"Unexpected '{token}' at position {pos}. Expected: {expected}",
            )

        action_type, value = act
        steps.append(ParseStep(stack[:], symbols[:], tokens[pos:], f"{action_type} {value}"))

        if action_type == 'shift':
            symbols.append(token)
            stack.append(value)
            pos += 1
        elif action_type == 'reduce':
            prod = table.grammar.productions[value]
            for _ in prod.body:
                stack.pop()
                symbols.pop()
            gs = table.goto_table.get((stack[-1], prod.head.name))
            if gs is None:
                return ParseResult(
                    accepted=False, steps=steps,
                    error=f"No GOTO for I{stack[-1]} on {prod.head}",
                )
            stack.append(gs)
            symbols.append(str(prod.head))
        elif action_type == 'accept':
            return ParseResult(accepted=True, steps=steps)
