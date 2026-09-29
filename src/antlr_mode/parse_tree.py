"""Árbol sintáctico común producido por el frontend de ANTLR."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParseTreeNode:
    """Representa una regla o terminal sin depender del runtime de ANTLR."""

    symbol: str
    children: list[ParseTreeNode] = field(default_factory=list)
    rule_name: str | None = None
    alternative: str | None = None
    token_type: str | None = None
    text: str | None = None
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None

    @property
    def is_leaf(self) -> bool:
        """Indica si el nodo no tiene descendientes."""
        return len(self.children) == 0


__all__ = ["ParseTreeNode"]
