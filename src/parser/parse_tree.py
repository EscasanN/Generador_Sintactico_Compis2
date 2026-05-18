from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ParseTreeNode:
    symbol: str
    children: list[ParseTreeNode] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0
