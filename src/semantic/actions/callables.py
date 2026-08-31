"""Generic function, call, return, recursion and closure actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.control_flow import FlowSignal
from src.semantic.diagnostics import DiagnosticCategory
from src.semantic.symbol_table import ScopeKind, Symbol, SymbolKind
from src.semantic.types import ERROR, UNKNOWN, VOID, FunctionType, Type, is_assignable
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.parser.parse_tree import ParseTreeNode
    from src.semantic.evaluator import SemanticContext


def declare_function(
    context: SemanticContext,
    node: ParseTreeNode,
    name: Any,
    parameter_types: Iterable[Type | str] = (),
    return_type: Type | str | None = VOID,
    parameter_names: Iterable[str] = (),
    kind: str = "function",
) -> SemanticValue:
    """Declare a callable before its body, enabling recursion and closures."""
    identifier = context.text_of(name)
    location = context.location_of(node)
    types = tuple(context.resolve_type(type_) for type_ in parameter_types)
    names = tuple(parameter_names)
    if names and len(names) != len(types):
        raise ValueError("parameter_names and parameter_types must have equal length")
    callable_type = FunctionType(types, context.resolve_type(return_type))
    symbol_kind = SymbolKind.METHOD if kind == "method" else SymbolKind.FUNCTION
    symbol = Symbol(
        identifier,
        symbol_kind,
        callable_type,
        False,
        location,
        {
            "parameter_names": names,
            "definition_scope": context.symbol_table.current_scope,
        },
    )
    if not context.symbol_table.declare(symbol):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            f"function '{identifier}' is already declared in this scope",
            location,
        )
        return SemanticValue(ERROR, location=location)
    return SemanticValue(callable_type, symbol=symbol, location=location)


def enter_function(
    context: SemanticContext,
    node: ParseTreeNode,
    function: SemanticValue | Symbol | Any,
) -> None:
    """Enter a function environment and make its declared parameters visible."""
    symbol = context.symbol_of(function)
    location = context.location_of(node)
    if symbol is None or not isinstance(symbol.type, FunctionType):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            "cannot enter an undeclared function",
            location,
        )
        context.function_stack.append(None)
        return
    context.function_stack.append(symbol)
    context.symbol_table.enter_scope(ScopeKind.FUNCTION, symbol.name, location)
    names = tuple(symbol.metadata.get("parameter_names", ()))
    for index, parameter_type in enumerate(symbol.type.parameter_types):
        parameter_name = names[index] if index < len(names) else f"parameter{index + 1}"
        parameter = Symbol(
            parameter_name,
            SymbolKind.PARAMETER,
            parameter_type,
            True,
            location,
        )
        if not context.symbol_table.declare(parameter):
            context.diagnostics.add(
                DiagnosticCategory.FUNCTION,
                f"duplicate parameter '{parameter_name}'",
                location,
            )


def exit_function(context: SemanticContext, node: ParseTreeNode) -> None:
    """Leave the current function and restore its lexical parent."""
    del node
    if context.function_stack:
        function = context.function_stack.pop()
        if function is None:
            return
        context.symbol_table.exit_scope()


def call_function(
    context: SemanticContext,
    node: ParseTreeNode,
    callee: SemanticValue | Symbol | Any,
    arguments: Iterable[SemanticValue] = (),
) -> SemanticValue:
    """Validate positional arity and argument compatibility (FUN-01)."""
    location = context.location_of(node)
    value = context.value_of(callee)
    arguments = tuple(
        argument for argument in arguments if isinstance(argument, SemanticValue)
    )
    if not isinstance(value.type, FunctionType):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            f"value of type {value.type} is not callable",
            location,
        )
        return SemanticValue(ERROR, location=location)
    signature = value.type
    if len(arguments) != len(signature.parameter_types):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            f"expected {len(signature.parameter_types)} arguments, got {len(arguments)}",
            location,
        )
        return SemanticValue(ERROR, location=location)
    invalid = False
    for index, (argument, expected) in enumerate(
        zip(arguments, signature.parameter_types), start=1
    ):
        if not is_assignable(argument.type, expected):
            context.diagnostics.add(
                DiagnosticCategory.FUNCTION,
                f"argument {index} expects {expected}, got {argument.type}",
                argument.location or location,
            )
            invalid = True
    return SemanticValue(ERROR if invalid else signature.return_type, location=location)


def return_value(
    context: SemanticContext,
    node: ParseTreeNode,
    value: SemanticValue | None = None,
) -> FlowSignal | SemanticValue:
    """Validate return placement and declared type (FUN-02/CTL-03)."""
    location = context.location_of(node)
    if not context.function_stack:
        context.diagnostics.add(
            DiagnosticCategory.CONTROL_FLOW,
            "return is only valid inside a function",
            location,
        )
        return SemanticValue(ERROR, location=location)
    function = context.function_stack[-1]
    if function is None:
        context.diagnostics.add(
            DiagnosticCategory.CONTROL_FLOW,
            "return is only valid inside a declared function",
            location,
        )
        return SemanticValue(ERROR, location=location)
    assert isinstance(function.type, FunctionType)
    actual = VOID if value is None else value.type
    expected = function.type.return_type
    if not is_assignable(actual, expected):
        context.diagnostics.add(
            DiagnosticCategory.FUNCTION,
            f"function '{function.name}' returns {expected}, got {actual}",
            location,
        )
    return FlowSignal.RETURN


def register_callable_actions(registry: ActionRegistry) -> None:
    """Register the stable callable action names."""
    registry.register("function.declare", declare_function)
    registry.register("function.enter", enter_function)
    registry.register("function.exit", exit_function)
    registry.register("function.call", call_function)
    registry.register("function.return", return_value)
