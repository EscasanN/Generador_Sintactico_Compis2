from __future__ import annotations
from dataclasses import dataclass, field

EPSILON = 'epsilon'
EOF = '$'


@dataclass(frozen=True)
class Symbol:
    name: str
    is_terminal: bool

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


EPSILON_SYM = Symbol(EPSILON, True)
EOF_SYM = Symbol(EOF, True)


@dataclass(frozen=True)
class Production:
    head: Symbol
    body: tuple[Symbol, ...]
    index: int

    def is_epsilon(self) -> bool:
        return len(self.body) == 0

    def __repr__(self) -> str:
        body_str = ' '.join(str(s) for s in self.body) if self.body else 'epsilon'
        return f"{self.head} -> {body_str}"


@dataclass
class Grammar:
    terminals: frozenset[Symbol]
    non_terminals: frozenset[Symbol]
    productions: list[Production]
    start: Symbol

    def productions_for(self, nt: Symbol) -> list[Production]:
        return [p for p in self.productions if p.head == nt]

    def augmented(self) -> Grammar:
        sp = Symbol(self.start.name + "'", False)
        aug_prod = Production(sp, (self.start,), 0)
        new_prods = [aug_prod] + [
            Production(p.head, p.body, i + 1)
            for i, p in enumerate(self.productions)
        ]
        return Grammar(
            terminals=self.terminals | {EOF_SYM},
            non_terminals=self.non_terminals | {sp},
            productions=new_prods,
            start=sp,
        )


class GrammarError(Exception):
    pass
