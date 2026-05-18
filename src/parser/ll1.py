from __future__ import annotations
from dataclasses import dataclass, field
from src.parser.grammar import Grammar, Symbol, Production, EPSILON_SYM
from src.parser.first_follow import compute_first, compute_follow, first_of_sequence
from src.parser.parse_tree import ParseTreeNode


class LL1Error(Exception):
    pass


def build_ll1_table(
    grammar: Grammar,
) -> tuple[dict[tuple[str, str], Production], list[str]]:
    """
    Build LL(1) predictive parsing table.

    Conflict policy: when two productions compete for the same M[A, t] cell,
    the first one (by definition order) wins. Conflicts are still recorded
    and returned so the UI can warn that the grammar is not strict LL(1).

    Returns:
        (table, conflicts) — conflicts is the list of M[NT, T] entries that
        were resolved by definition order.
    """
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table: dict[tuple[str, str], Production] = {}
    conflicts: list[str] = []

    def assign(key: tuple[str, str], prod: Production) -> None:
        if key in table:
            existing = table[key]
            conflicts.append(
                f"M[{key[0]},{key[1]}]: kept {existing} (defined first), "
                f"skipped {prod}"
            )
            return
        table[key] = prod

    for prod in grammar.productions:
        fa = first_of_sequence(prod.body, first)
        for sym in fa:
            if sym == EPSILON_SYM:
                continue
            assign((prod.head.name, sym.name), prod)
        if EPSILON_SYM in fa:
            for sym in follow.get(prod.head, set()):
                assign((prod.head.name, sym.name), prod)

    return table, conflicts


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
    tree: ParseTreeNode | None = None


def ll1_parse(
    tokens: list[str],
    table: dict[tuple[str, str], Production],
    grammar: Grammar,
    max_steps: int | None = None,
) -> LL1ParseResult:
    """tokens must end with '$'.

    Safety: when the grammar has unresolved left-recursion (typical when the
    LL(1) table was built with first-wins conflict resolution), the parser
    can loop forever expanding the same non-terminal. We cap total iterations
    to `max_steps` and report a descriptive error.
    """
    root = ParseTreeNode(str(grammar.start))
    parse_stack: list[str] = ['$', str(grammar.start)]
    node_stack: list[ParseTreeNode | None] = [None, root]
    pos = 0
    steps: list[LL1ParseStep] = []
    cap = max_steps if max_steps is not None else max(1000, len(tokens) * 200)

    while parse_stack[-1] != '$':
        if len(steps) >= cap:
            return LL1ParseResult(
                accepted=False, steps=steps,
                error=(
                    f"LL(1) parse exceeded {cap} steps — likely left-recursion "
                    f"in the grammar (unresolvable by first-wins disambiguation)."
                ),
                tree=root,
            )
        top = parse_stack[-1]
        top_node = node_stack[-1]
        token = tokens[pos] if pos < len(tokens) else '$'

        if top == token:
            steps.append(LL1ParseStep(parse_stack[:], tokens[pos:], f"match {token}"))
            parse_stack.pop()
            node_stack.pop()
            pos += 1
        else:
            prod = table.get((top, token))
            if prod is None:
                expected = sorted({t for nt, t in table if nt == top})
                return LL1ParseResult(
                    accepted=False, steps=steps,
                    error=f"Unexpected '{token}' for '{top}'. Expected: {expected}",
                )
            steps.append(LL1ParseStep(parse_stack[:], tokens[pos:], f"expand {prod}"))
            parse_stack.pop()
            node_stack.pop()

            if prod.is_epsilon():
                children = [ParseTreeNode('ε')]
            else:
                children = [
                    ParseTreeNode(sym.name)
                    for sym in prod.body
                    if sym != EPSILON_SYM
                ]

            if top_node is not None:
                top_node.children = children

            for child in reversed(children):
                parse_stack.append(child.symbol)
                node_stack.append(child)

    token = tokens[pos] if pos < len(tokens) else '$'
    if parse_stack[-1] == '$' and token == '$':
        return LL1ParseResult(accepted=True, steps=steps, tree=root)
    return LL1ParseResult(
        accepted=False, steps=steps,
        error=f"Incomplete parse. Stack: {parse_stack}",
    )
