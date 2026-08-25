from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ParseTreeNode:
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
        return len(self.children) == 0
