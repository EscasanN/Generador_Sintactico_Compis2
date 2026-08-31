"""Generic class, member, constructor and ``this`` actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.callables import call_function, declare_function
from src.semantic.diagnostics import DiagnosticCategory
from src.semantic.symbol_table import ScopeKind, Symbol, SymbolKind
from src.semantic.types import ERROR, UNKNOWN, VOID, ClassType, Type
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.parser.parse_tree import ParseTreeNode
    from src.semantic.evaluator import SemanticContext


def declare_class(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
) -> SemanticValue:
    """Declare a class and initialize its grammar-neutral member directory."""
    identifier = context.text_of(name)
    location = context.location_of(node)
    class_type = ClassType(identifier)
    members: dict[str, Symbol] = {}
    symbol = Symbol(
        identifier,
        SymbolKind.CLASS,
        class_type,
        False,
        location,
        {"members": members},
    )
    if not context.symbol_table.declare(symbol):
        context.diagnostics.add(
            DiagnosticCategory.SCOPE,
            f"class '{identifier}' is already declared in this scope",
            location,
        )
        return SemanticValue(ERROR, location=location)
    context.classes[identifier] = symbol
    return SemanticValue(class_type, symbol=symbol, location=location)


def enter_class(
    context: SemanticContext,
    node: ParseTreeNode,
    class_: SemanticValue | Symbol | Any,
) -> None:
    """Enter a class environment used by fields, methods and ``this``."""
    symbol = context.symbol_of(class_)
    if symbol is None or symbol.kind is not SymbolKind.CLASS:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            "cannot enter an undeclared class",
            context.location_of(node),
        )
        context.class_stack.append(None)
        return
    context.class_stack.append(symbol)
    context.symbol_table.enter_scope(
        ScopeKind.CLASS, symbol.name, context.location_of(node)
    )


def exit_class(context: SemanticContext, node: ParseTreeNode) -> None:
    """Leave the current class environment."""
    del node
    if context.class_stack:
        class_symbol = context.class_stack.pop()
        if class_symbol is None:
            return
        context.symbol_table.exit_scope()


def declare_field(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    type_: Type | str | None = None,
    mutable: bool = True,
) -> SemanticValue:
    """Register one field in both the class scope and member directory."""
    location = context.location_of(node)
    if not context.class_stack or context.class_stack[-1] is None:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            "a field declaration requires a class context",
            location,
        )
        return SemanticValue(ERROR, location=location)
    identifier = context.text_of(name)
    symbol = Symbol(
        identifier,
        SymbolKind.FIELD,
        context.resolve_type(type_),
        mutable,
        location,
    )
    if not context.symbol_table.declare(symbol):
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            f"member '{identifier}' is already declared in this class",
            location,
        )
        return SemanticValue(ERROR, location=location)
    class_symbol = context.class_stack[-1]
    assert class_symbol is not None
    members = class_symbol.metadata["members"]
    members[identifier] = symbol
    return SemanticValue(
        symbol.type,
        assignable=True,
        mutable=mutable,
        symbol=symbol,
        location=location,
    )


def declare_method(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    parameter_types: Iterable[Type | str] = (),
    return_type: Type | str | None = VOID,
    parameter_names: Iterable[str] = (),
    constructor: bool = False,
) -> SemanticValue:
    """Register a method or constructor with a positional signature."""
    location = context.location_of(node)
    if not context.class_stack or context.class_stack[-1] is None:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            "a method declaration requires a class context",
            location,
        )
        return SemanticValue(ERROR, location=location)
    identifier = "constructor" if constructor else context.text_of(name)
    value = declare_function(
        context,
        node,
        identifier,
        parameter_types,
        context.resolve_type(return_type),
        parameter_names,
        kind="method",
    )
    if value.symbol is not None and value.type != ERROR:
        class_symbol = context.class_stack[-1]
        assert class_symbol is not None
        class_symbol.metadata["members"][identifier] = value.symbol
    return value


def access_member(
    context: SemanticContext,
    node: ParseTreeNode,
    instance: SemanticValue,
    name: Any,
) -> SemanticValue:
    """Resolve a declared field or method (CLS-01)."""
    location = context.location_of(node)
    identifier = context.text_of(name)
    if instance.type in {ERROR, UNKNOWN}:
        return SemanticValue(instance.type, location=location)
    if not isinstance(instance.type, ClassType):
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            f"type {instance.type} has no members",
            location,
        )
        return SemanticValue(ERROR, location=location)
    class_symbol = context.classes.get(instance.type.name)
    if class_symbol is not None:
        member = class_symbol.metadata["members"].get(identifier)
        if member is not None:
            return SemanticValue(
                member.type,
                assignable=member.kind is SymbolKind.FIELD,
                mutable=member.mutable,
                symbol=member,
                location=location,
            )
    context.diagnostics.add(
        DiagnosticCategory.CLASS,
        f"class '{instance.type.name}' has no member '{identifier}'",
        location,
    )
    return SemanticValue(ERROR, location=location)


def construct(
    context: SemanticContext,
    node: ParseTreeNode,
    class_: SemanticValue | Symbol | Any,
    arguments: Iterable[SemanticValue] = (),
) -> SemanticValue:
    """Validate a constructor invocation and return an instance value."""
    location = context.location_of(node)
    symbol = context.symbol_of(class_)
    if symbol is None or symbol.kind is not SymbolKind.CLASS:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            f"unknown class '{context.text_of(class_)}'",
            location,
        )
        return SemanticValue(ERROR, location=location)
    constructor_symbol = symbol.metadata["members"].get("constructor")
    if constructor_symbol is None:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            f"class '{symbol.name}' has no constructor",
            location,
        )
        return SemanticValue(ERROR, location=location)
    result = call_function(context, node, constructor_symbol, arguments)
    if result.type == ERROR:
        return result
    return SemanticValue(symbol.type, location=location)


def this_value(context: SemanticContext, node: ParseTreeNode) -> SemanticValue:
    """Resolve ``this`` only while a class context is active (CLS-03)."""
    location = context.location_of(node)
    if not context.class_stack or context.class_stack[-1] is None:
        context.diagnostics.add(
            DiagnosticCategory.CLASS,
            "this is only valid inside a class",
            location,
        )
        return SemanticValue(ERROR, location=location)
    symbol = context.class_stack[-1]
    assert symbol is not None
    return SemanticValue(symbol.type, symbol=symbol, location=location)


def register_class_actions(registry: ActionRegistry) -> None:
    """Register stable class action names."""
    registry.register("class.declare", declare_class)
    registry.register("class.enter", enter_class)
    registry.register("class.exit", exit_class)
    registry.register("class.field", declare_field)
    registry.register("class.method", declare_method)
    registry.register("class.member", access_member)
    registry.register("class.construct", construct)
    registry.register("class.this", this_value)
