"""Generic condition, loop-context and unreachable-code actions."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Iterable

from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.declarations import declare_variable
from src.semantic.diagnostics import DiagnosticCategory, DiagnosticSeverity
from src.semantic.types import ERROR, UNKNOWN, BOOLEAN, ArrayType
from src.semantic.values import SemanticValue

if TYPE_CHECKING:
    from src.antlr_mode.parse_tree import ParseTreeNode
    from src.semantic.evaluator import SemanticContext


class FlowSignal(Enum):
    """Definitive transfers used only during static traversal."""

    RETURN = "return"
    BREAK = "break"
    CONTINUE = "continue"


def require_boolean_condition(
    context: SemanticContext,
    node: ParseTreeNode,
    condition: SemanticValue,
    construct: str = "control structure",
) -> SemanticValue:
    """Require a boolean condition for every configured control structure."""
    location = condition.location or context.location_of(node)
    if condition.type in {ERROR, UNKNOWN}:
        return SemanticValue(condition.type, location=location)
    if condition.type != BOOLEAN:
        context.diagnostics.add(
            DiagnosticCategory.CONTROL_FLOW,
            f"{construct} condition must be boolean, got {condition.type}",
            location,
        )
        return SemanticValue(ERROR, location=location)
    return condition


def enter_loop(
    context: SemanticContext,
    node: ParseTreeNode,
    name: str = "loop",
) -> None:
    """Mark a loop context for nested break and continue actions."""
    context.loop_stack.append((name, context.location_of(node)))


def exit_loop(context: SemanticContext, node: ParseTreeNode) -> None:
    """Leave the nearest loop context."""
    del node
    if context.loop_stack:
        context.loop_stack.pop()


def bind_foreach_iterator(
    context: SemanticContext,
    node: ParseTreeNode,
    name: object,
    iterable: SemanticValue,
) -> SemanticValue:
    """Validate an array iterable and bind its element type in the loop scope."""
    value = context.value_of(iterable)
    if isinstance(value.type, ArrayType):
        iterator_type = value.type.element_type
    elif value.type in {ERROR, UNKNOWN}:
        iterator_type = value.type
    else:
        context.diagnostics.add(
            DiagnosticCategory.ARRAY,
            f"foreach requires an array iterable, got {value.type}",
            value.location or context.location_of(node),
        )
        iterator_type = ERROR
    return declare_variable(context, node, name, iterator_type)


def break_loop(context: SemanticContext, node: ParseTreeNode) -> FlowSignal | None:
    """Validate that ``break`` is nested in a loop (CTL-02)."""
    if not context.loop_stack:
        context.diagnostics.add(
            DiagnosticCategory.CONTROL_FLOW,
            "break is only valid inside a loop",
            context.location_of(node),
        )
        return None
    return FlowSignal.BREAK


def continue_loop(context: SemanticContext, node: ParseTreeNode) -> FlowSignal | None:
    """Validate that ``continue`` is nested in a loop (CTL-02)."""
    if not context.loop_stack:
        context.diagnostics.add(
            DiagnosticCategory.CONTROL_FLOW,
            "continue is only valid inside a loop",
            context.location_of(node),
        )
        return None
    return FlowSignal.CONTINUE


def validate_sequence(
    context: SemanticContext,
    node: ParseTreeNode,
    statements: Iterable[object],
) -> FlowSignal | None:
    """Warn for statements following a definitive transfer (GEN-01)."""
    transfer: FlowSignal | None = None
    children = tuple(getattr(node, "children", ()))
    for index, result in enumerate(statements):
        if transfer is not None:
            child = children[index] if index < len(children) else node
            context.diagnostics.add(
                DiagnosticCategory.GENERAL,
                f"unreachable instruction after {transfer.value}",
                context.location_of(child),
                DiagnosticSeverity.WARNING,
            )
            continue
        if isinstance(result, FlowSignal):
            transfer = result
    return transfer


def register_control_flow_actions(registry: ActionRegistry) -> None:
    """Register stable control-flow action names."""
    registry.register("control.condition", require_boolean_condition)
    registry.register("loop.enter", enter_loop)
    registry.register("loop.exit", exit_loop)
    registry.register("loop.bind_iterator", bind_foreach_iterator)
    registry.register("control.break", break_loop)
    registry.register("control.continue", continue_loop)
    registry.register("control.sequence", validate_sequence)
