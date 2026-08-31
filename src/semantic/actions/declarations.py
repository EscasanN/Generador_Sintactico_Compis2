"""Generic declaration, scope and identifier actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.semantic.action_registry import ActionRegistry
from src.semantic.diagnostics import DiagnosticCategory
from src.semantic.symbol_table import ScopeKind, Symbol, SymbolKind
from src.semantic.types import ERROR, UNKNOWN, Type, is_assignable, type_from_name
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.parser.parse_tree import ParseTreeNode
    from src.semantic.evaluator import SemanticContext


def declare_variable(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    type_: Type | str | None = None,
    initializer: SemanticValue | None = None,
    mutable: bool = True,
) -> SemanticValue:
    """Declare a variable or constant and validate its initializer."""
    identifier = context.text_of(name)
    location = context.location_of(node)
    declared_type = context.resolve_type(type_)
    if type_ is None and initializer is not None:
        declared_type = initializer.type
    kind = SymbolKind.VARIABLE if mutable else SymbolKind.CONSTANT

    if not mutable and initializer is None:
        context.diagnostics.add(
            DiagnosticCategory.TYPE,
            f"constant '{identifier}' must be initialized when declared",
            location,
        )
    if initializer is not None and declared_type != UNKNOWN:
        if not is_assignable(initializer.type, declared_type):
            context.diagnostics.add(
                DiagnosticCategory.TYPE,
                f"cannot initialize '{identifier}' of type {declared_type} "
                f"with {initializer.type}",
                location,
            )
            declared_type = ERROR

    symbol = Symbol(identifier, kind, declared_type, mutable, location)
    if not context.symbol_table.declare(symbol):
        context.diagnostics.add(
            DiagnosticCategory.SCOPE,
            f"'{identifier}' is already declared in this scope",
            location,
        )
        return SemanticValue(ERROR, location=location)
    return SemanticValue(
        declared_type,
        assignable=True,
        mutable=mutable,
        symbol=symbol,
        location=location,
    )


def declare_constant(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    type_: Type | str | None = None,
    initializer: SemanticValue | None = None,
) -> SemanticValue:
    """Declare an immutable value that requires an initializer (TYP-05)."""
    return declare_variable(context, node, name, type_, initializer, mutable=False)


def declare_parameter(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    type_: Type | str | None = None,
) -> SemanticValue:
    """Declare one function parameter, rejecting duplicate names (GEN-03)."""
    identifier = context.text_of(name)
    location = context.location_of(node)
    parameter_type = context.resolve_type(type_)
    symbol = Symbol(
        identifier,
        SymbolKind.PARAMETER,
        parameter_type,
        True,
        location,
    )
    if not context.symbol_table.declare(symbol):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            f"duplicate parameter '{identifier}'",
            location,
        )
        return SemanticValue(ERROR, location=location)
    return SemanticValue(
        parameter_type,
        assignable=True,
        mutable=True,
        symbol=symbol,
        location=location,
    )


def resolve_identifier(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any | None = None,
) -> SemanticValue:
    """Resolve the nearest visible declaration (SCP-01/SCP-03)."""
    identifier = context.text_of(node if name is None else name)
    location = context.location_of(node)
    symbol = context.symbol_table.resolve(identifier)
    if symbol is None:
        context.diagnostics.add(
            DiagnosticCategory.SCOPE,
            f"undeclared identifier '{identifier}'",
            location,
        )
        return SemanticValue(ERROR, location=location)
    return SemanticValue(
        symbol.type,
        assignable=symbol.kind
        in {SymbolKind.VARIABLE, SymbolKind.CONSTANT, SymbolKind.PARAMETER, SymbolKind.FIELD},
        mutable=symbol.mutable,
        symbol=symbol,
        location=location,
    )


def enter_scope(
    context: SemanticContext,
    node: ParseTreeNode,
    kind: str = "block",
    name: str | None = None,
) -> None:
    """Open a named lexical scope."""
    try:
        scope_kind = ScopeKind(kind)
    except ValueError as exc:
        raise ValueError(f"unsupported scope kind: {kind}") from exc
    context.symbol_table.enter_scope(
        scope_kind,
        name or f"{kind}@{context.location_of(node).line}",
        context.location_of(node),
    )


def exit_scope(context: SemanticContext, node: ParseTreeNode) -> None:
    """Close the current lexical scope while retaining it in the table."""
    del node
    context.symbol_table.exit_scope()


def register_declaration_actions(registry: ActionRegistry) -> None:
    """Register the stable declaration action names."""
    registry.register("declare.variable", declare_variable)
    registry.register("declare.constant", declare_constant)
    registry.register("declare.parameter", declare_parameter)
    registry.register("identifier.resolve", resolve_identifier)
    registry.register("scope.enter", enter_scope)
    registry.register("scope.exit", exit_scope)
