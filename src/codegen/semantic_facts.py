"""The real ``SemanticFacts`` adapter backed by annotations and layouts.

Nodes are looked up by identity: the same ``ParseTreeNode`` objects retained by
the syntax result that was analysed. Names are never searched again once a
``Symbol`` has been resolved.
"""

from __future__ import annotations

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.activation import (
    CALLABLE_KINDS,
    ActivationRecordLayout,
    RuntimeLayouts,
    build_runtime_layouts,
    enclosing_function,
    function_symbol_of,
    lexical_level,
    parent_function,
)
from src.codegen.contracts import Address, LexicalAccess
from src.codegen.layout import StorageClass
from src.semantic.results import SemanticAnalysisResult, SemanticAnnotations
from src.semantic.symbol_table import Scope, Symbol, SymbolKind, SymbolTable
from src.semantic.types import ClassType, Type
from src.semantic.values import SemanticValue

LOCAL = "local"
GLOBAL = "global"
FIELD = "field"
CAPTURED = "captured"
METHOD = "method"


class MissingFactError(LookupError):
    """A fact required by the generator is absent from the annotations."""


class SemanticFactsIndex:
    """Implements the ``SemanticFacts`` protocol of ``contracts.py``."""

    def __init__(
        self,
        annotations: SemanticAnnotations,
        symbol_table: SymbolTable,
        layouts: RuntimeLayouts,
    ) -> None:
        self.annotations = annotations
        self.symbol_table = symbol_table
        self.layouts = layouts
        self._owner = dict(layouts.captures.owner_scope)

    @classmethod
    def from_result(
        cls,
        result: SemanticAnalysisResult,
        root: ParseTreeNode | None = None,
    ) -> "SemanticFactsIndex":
        """Build layouts and facts from an accepted semantic result.

        ``root`` is the syntax tree that was analysed; with it a closure whose
        function is only ever called directly keeps a stack environment instead
        of being conservatively marked as heap-allocated.
        """
        layouts = build_runtime_layouts(result.symbol_table, result.annotations, root)
        return cls(result.annotations, result.symbol_table, layouts)

    # -- SemanticFacts protocol -------------------------------------------------

    def value_for(self, node: ParseTreeNode) -> SemanticValue:
        value = self.annotations.value_for(node)
        if value is None:
            raise MissingFactError(f"no SemanticValue for node {_describe(node)}")
        return value

    def symbol_for(self, node: ParseTreeNode) -> Symbol | None:
        return self.annotations.symbol_for(node)

    def scope_for(self, node: ParseTreeNode) -> Scope:
        scope = self.annotations.scope_for(node)
        if scope is None:
            raise MissingFactError(f"no Scope for node {_describe(node)}")
        return scope

    def address_for(self, symbol: Symbol) -> Address:
        return self.layouts.symbols.address_for(symbol)

    def member_offset(self, owner: Type, name: str) -> int:
        if not isinstance(owner, ClassType):
            raise LookupError(f"type {owner} has no members")
        return self.layouts.class_layout(owner).field_offset(name)

    def lexical_access(self, node: ParseTreeNode, symbol: Symbol) -> LexicalAccess:
        """Classify a reference as local, global, field, method or captured."""
        layout = self.layouts.symbols.layout_for(symbol)
        if layout.storage is StorageClass.FIELD:
            return LexicalAccess(FIELD, 0, layout.offset)
        declared = self._owner.get(id(symbol))
        declaring_function = enclosing_function(declared)
        if symbol.kind is SymbolKind.METHOD:
            return LexicalAccess(METHOD, 0, None)
        if symbol.kind in CALLABLE_KINDS or symbol.kind is SymbolKind.CLASS:
            return LexicalAccess(GLOBAL if declaring_function is None else LOCAL, 0, None)
        if layout.storage is StorageClass.STATIC:
            return LexicalAccess(GLOBAL, 0, layout.offset)
        user = enclosing_function(self.scope_for(node))
        if user is None or declaring_function is None:
            raise LookupError(f"'{symbol.name}' is not reachable from a global reference")
        if user is declaring_function:
            return LexicalAccess(LOCAL, 0, layout.offset)
        if not _encloses(declaring_function, user) or layout.env_offset is None:
            raise LookupError(f"'{symbol.name}' is not captured by the function using it")
        depth = lexical_level(user) - lexical_level(declaring_function) - 1
        return LexicalAccess(CAPTURED, depth, layout.env_offset)

    # -- conveniences for the generator ----------------------------------------

    def activation_for(self, node: ParseTreeNode) -> ActivationRecordLayout:
        """Activation record of the function containing ``node`` (or global code)."""
        function = enclosing_function(self.scope_for(node))
        if function is None:
            return self.layouts.global_frame
        symbol = function_symbol_of(function)
        if symbol is None:
            raise MissingFactError(f"function scope '{function.name}' has no symbol")
        return self.layouts.frame_for(symbol)

    def label_for(self, symbol: Symbol) -> str:
        """Unique label of a function, method or class symbol."""
        label = self.layouts.symbols.layout_for(symbol).label
        if label is None:
            raise LookupError(f"'{symbol.name}' has no label")
        return label

    def declaring_scope(self, symbol: Symbol) -> Scope:
        try:
            return self._owner[id(symbol)]
        except KeyError:
            raise LookupError(f"symbol '{symbol.name}' is not in the symbol table") from None


def _encloses(candidate: Scope, scope: Scope) -> bool:
    current: Scope | None = scope
    while current is not None:
        if current is candidate:
            return True
        current = parent_function(current)
    return False


def _describe(node: object) -> str:
    rule = getattr(node, "rule_name", None) or getattr(node, "symbol", "?")
    return f"{rule}@{getattr(node, 'line', '?')}:{getattr(node, 'column', '?')}"
