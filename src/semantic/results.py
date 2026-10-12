"""Immutable public result produced by the generic semantic evaluator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from src.semantic.diagnostics import Diagnostic, DiagnosticSeverity
from src.semantic.symbol_table import Scope, Symbol, SymbolTable
from src.semantic.values import SemanticValue


def _frozen(mapping: Mapping[int, object]) -> Mapping[int, object]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True, slots=True)
class SemanticAnnotations:
    """Per-node semantic facts, keyed by the identity of the ``ParseTreeNode``.

    ``values_by_node`` keeps the ``SemanticValue`` produced for a node,
    ``symbols_by_node`` the resolved ``Symbol`` (by identity, never by name) and
    ``scopes_by_node`` the lexical scope active once the node's entry actions ran.
    ``anchors`` retains the annotated nodes so an ``id`` can never be recycled
    while the result is alive. All mappings are read-only.
    """

    values_by_node: Mapping[int, SemanticValue] = field(default_factory=dict)
    symbols_by_node: Mapping[int, Symbol] = field(default_factory=dict)
    scopes_by_node: Mapping[int, Scope] = field(default_factory=dict)
    anchors: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values_by_node", _frozen(self.values_by_node))
        object.__setattr__(self, "symbols_by_node", _frozen(self.symbols_by_node))
        object.__setattr__(self, "scopes_by_node", _frozen(self.scopes_by_node))
        object.__setattr__(self, "anchors", tuple(self.anchors))

    def value_for(self, node: object) -> SemanticValue | None:
        """Return the semantic value computed for ``node``, if any."""
        return self.values_by_node.get(id(node))

    def symbol_for(self, node: object) -> Symbol | None:
        """Return the symbol resolved or declared at ``node``, if any."""
        return self.symbols_by_node.get(id(node))

    def scope_for(self, node: object) -> Scope | None:
        """Return the lexical scope active at ``node``, if recorded."""
        return self.scopes_by_node.get(id(node))

    @classmethod
    def from_traversal(
        cls,
        results: Mapping[int, object],
        scopes: Mapping[int, Scope],
        resolved_symbols: Mapping[int, Symbol],
        predeclared_symbols: Mapping[int, Symbol | None],
        anchors: Mapping[int, object],
    ) -> "SemanticAnnotations":
        """Derive the immutable index from the evaluator's traversal state."""
        values: dict[int, SemanticValue] = {}
        symbols: dict[int, Symbol] = {}
        for node_id, result in results.items():
            if isinstance(result, SemanticValue):
                values[node_id] = result
                if isinstance(result.symbol, Symbol):
                    symbols[node_id] = result.symbol
        for node_id, predeclared in predeclared_symbols.items():
            if isinstance(predeclared, Symbol):
                symbols[node_id] = predeclared
        symbols.update(resolved_symbols)
        return cls(values, symbols, dict(scopes), tuple(anchors.values()))


@dataclass(frozen=True, slots=True)
class SemanticAnalysisResult:
    """Expose diagnostics, retained scopes, final value and traversal counts."""

    diagnostics: tuple[Diagnostic, ...]
    symbol_table: SymbolTable
    value: SemanticValue | None = None
    statistics: Mapping[str, int] = field(default_factory=dict)
    annotations: SemanticAnnotations = field(default_factory=SemanticAnnotations)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))

    @property
    def accepted(self) -> bool:
        """Return true when no semantic error was accumulated."""
        return not any(
            diagnostic.severity is DiagnosticSeverity.ERROR
            for diagnostic in self.diagnostics
        )
