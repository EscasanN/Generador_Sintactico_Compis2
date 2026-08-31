"""Persistent lexical scopes and symbols for the generic semantic engine."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.semantic.diagnostics import SourceLocation
from src.semantic.types import Type


class ScopeKind(Enum):
    """Kinds of lexical environment preserved for presentation."""

    GLOBAL = "global"
    FUNCTION = "function"
    CLASS = "class"
    BLOCK = "block"


class SymbolKind(Enum):
    """Kinds of declaration stored in a scope."""

    VARIABLE = "variable"
    CONSTANT = "constant"
    PARAMETER = "parameter"
    FUNCTION = "function"
    CLASS = "class"
    FIELD = "field"
    METHOD = "method"


@dataclass(frozen=True, slots=True)
class Symbol:
    """Describe one immutable source declaration.

    ``metadata`` is copied into a read-only mapping so callable and class
    actions can attach signatures, members and closure information safely.
    """

    name: str
    kind: SymbolKind
    type: Type
    mutable: bool
    location: SourceLocation
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("symbol name cannot be empty")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class Scope:
    """A lexical environment whose declarations survive after it is closed."""

    def __init__(
        self,
        kind: ScopeKind,
        name: str,
        location: SourceLocation | None,
        parent: Scope | None = None,
    ) -> None:
        self.kind = kind
        self.name = name
        self.location = location
        self.parent = parent
        self._symbols: dict[str, Symbol] = {}
        self._children: list[Scope] = []
        self.closed = False

    def declare(self, symbol: Symbol) -> bool:
        """Declare locally, returning ``False`` for a duplicate name."""
        if symbol.name in self._symbols:
            return False
        self._symbols[symbol.name] = symbol
        return True

    def resolve_local(self, name: str) -> Symbol | None:
        """Resolve only inside this scope."""
        return self._symbols.get(name)

    def resolve(self, name: str) -> Symbol | None:
        """Resolve the nearest declaration in this scope or an ancestor."""
        scope: Scope | None = self
        while scope is not None:
            symbol = scope.resolve_local(name)
            if symbol is not None:
                return symbol
            scope = scope.parent
        return None

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        """Return declarations in source insertion order."""
        return tuple(self._symbols.values())

    @property
    def children(self) -> tuple[Scope, ...]:
        """Return an immutable snapshot of direct child scopes."""
        return tuple(self._children)


class SymbolTable:
    """Manage a scope stack while retaining every scope ever entered."""

    def __init__(
        self,
        global_name: str = "global",
        location: SourceLocation | None = None,
    ) -> None:
        self.global_scope = Scope(ScopeKind.GLOBAL, global_name, location)
        self.current_scope = self.global_scope
        self._scopes: list[Scope] = [self.global_scope]

    def enter_scope(
        self,
        kind: ScopeKind,
        name: str,
        location: SourceLocation | None = None,
    ) -> Scope:
        """Create and enter a child of the current scope."""
        if kind is ScopeKind.GLOBAL:
            raise ValueError("a symbol table has exactly one global scope")
        scope = Scope(kind, name, location, self.current_scope)
        self.current_scope._children.append(scope)
        self._scopes.append(scope)
        self.current_scope = scope
        return scope

    def exit_scope(self) -> Scope:
        """Close the current scope and restore its parent."""
        if self.current_scope is self.global_scope:
            raise RuntimeError("cannot exit the global scope")
        closed = self.current_scope
        closed.closed = True
        assert closed.parent is not None
        self.current_scope = closed.parent
        return closed

    def declare(self, symbol: Symbol) -> bool:
        """Declare a symbol in the current scope."""
        return self.current_scope.declare(symbol)

    def resolve(self, name: str) -> Symbol | None:
        """Resolve from the current lexical environment."""
        return self.current_scope.resolve(name)

    def iter_scopes(self) -> Iterator[Scope]:
        """Iterate over all scopes in creation order, including closed ones."""
        return iter(tuple(self._scopes))

    def restore_global(self) -> None:
        """Close every open child scope after an interrupted traversal."""
        while self.current_scope is not self.global_scope:
            self.exit_scope()
