"""Stable facts and value contracts between semantic analysis and codegen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.ir import Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Scope, Symbol
from src.semantic.types import Type
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.codegen.builder import IRBuilder


@dataclass(frozen=True, slots=True)
class Address:
    """A stable abstract address retaining the resolved Symbol by identity."""

    symbol: Symbol
    storage: str
    name: str
    offset: int | None = None
    scope: str | None = None

    def __str__(self) -> str:
        prefix = self.storage if self.scope is None else f"{self.storage}:{self.scope}"
        position = "" if self.offset is None else f"[{self.offset}]"
        return f"{prefix}{position}@{self.name}"


@dataclass(frozen=True, slots=True)
class LexicalAccess:
    """A semantic description of access to a local, global, or captured symbol."""

    kind: str
    depth: int = 0
    offset: int | None = None


class SemanticFacts(Protocol):
    """Queries Nadissa's adapter must provide without reparsing source text."""

    def value_for(self, node: ParseTreeNode) -> SemanticValue: ...

    def symbol_for(self, node: ParseTreeNode) -> Symbol | None: ...

    def scope_for(self, node: ParseTreeNode) -> Scope: ...

    def address_for(self, symbol: Symbol) -> Address: ...

    def member_offset(self, owner: Type, name: str) -> int: ...

    def lexical_access(self, node: ParseTreeNode, symbol: Symbol) -> LexicalAccess: ...


class CodegenError(RuntimeError):
    """A code generation contract failure with stable code and source location."""

    def __init__(self, code: str, message: str, location: SourceLocation | None = None) -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class ValueRef:
    """An expression value and whether its caller owns a temporary lease."""

    operand: Operand
    type: Type
    owns_temporary: bool = False
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if self.owns_temporary != (self.operand.kind is OperandKind.TEMPORARY):
            raise ValueError("temporary ownership must match the operand kind")

    def release(self, builder: "IRBuilder", location: SourceLocation | None = None) -> None:
        """Release an owned lease after its final use; immediates need no action."""
        if self.owns_temporary:
            builder.release(self.operand, location or self.location)
