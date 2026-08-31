"""Grammar-neutral traversal and action execution over ``ParseTreeNode``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.parser.parse_tree import ParseTreeNode
from src.semantic.action_registry import ActionRegistry
from src.semantic.actions import register_builtin_actions
from src.semantic.diagnostics import DiagnosticBag, SourceLocation
from src.semantic.expression_actions import ExpressionActions
from src.semantic.profile import (
    ActionInvocation,
    ChildSelector,
    ProfileError,
    SemanticProfile,
    resolve_binding,
)
from src.semantic.results import SemanticAnalysisResult
from src.semantic.symbol_table import Symbol, SymbolKind, SymbolTable
from src.semantic.types import ERROR, UNKNOWN, ClassType, Type, type_from_name
from src.semantic.values import SemanticValue


@dataclass(slots=True)
class SemanticContext:
    """Mutable state shared by actions during exactly one analysis."""

    diagnostics: DiagnosticBag = field(default_factory=DiagnosticBag)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)
    source_path: str | None = None
    function_stack: list[Symbol | None] = field(default_factory=list)
    class_stack: list[Symbol | None] = field(default_factory=list)
    loop_stack: list[object] = field(default_factory=list)
    results: dict[int, object] = field(default_factory=dict)
    classes: dict[str, Symbol] = field(default_factory=dict)
    expressions: ExpressionActions = field(init=False)

    def __post_init__(self) -> None:
        self.expressions = ExpressionActions(self.diagnostics)

    def location_of(self, node: ParseTreeNode | object) -> SourceLocation:
        """Build a one-based location, using a safe fallback for manual trees."""
        return SourceLocation(
            max(int(getattr(node, "line", None) or 1), 1),
            max(int(getattr(node, "column", None) or 1), 1),
            _positive_or_none(getattr(node, "end_line", None)),
            _positive_or_none(getattr(node, "end_column", None)),
            self.source_path,
        )

    def text_of(self, value: object) -> str:
        """Extract declarative text without evaluating Python expressions."""
        if isinstance(value, str):
            return value
        if isinstance(value, Symbol):
            return value.name
        if isinstance(value, SemanticValue) and value.symbol is not None:
            return value.symbol.name
        text = getattr(value, "text", None)
        if text is not None:
            return str(text)
        symbol = getattr(value, "symbol", None)
        if isinstance(symbol, str):
            return symbol
        raise ValueError("value does not provide source text")

    def resolve_type(self, value: object) -> Type:
        """Resolve primitives and classes already declared in this context."""
        if isinstance(value, Type):
            return value
        if isinstance(value, SemanticValue):
            return value.type
        if isinstance(value, Symbol):
            return value.type
        if value is None:
            return UNKNOWN
        if not isinstance(value, str):
            try:
                value = self.text_of(value)
            except ValueError:
                return UNKNOWN
        array_depth = 0
        value = value.strip()
        while value.endswith("[]"):
            array_depth += 1
            value = value[:-2].rstrip()
        return type_from_name(
            value,
            array_depth=array_depth,
            class_lookup=lambda name: (
                self.classes[name].type
                if name in self.classes
                and isinstance(self.classes[name].type, ClassType)
                else None
            ),
        )

    def value_of(self, value: object) -> SemanticValue:
        """Normalize selected nodes and symbols into semantic values."""
        if isinstance(value, SemanticValue):
            return value
        if isinstance(value, Symbol):
            return SemanticValue(
                value.type,
                assignable=value.kind
                in {
                    SymbolKind.VARIABLE,
                    SymbolKind.CONSTANT,
                    SymbolKind.PARAMETER,
                    SymbolKind.FIELD,
                },
                mutable=value.mutable,
                symbol=value,
                location=value.location,
            )
        if isinstance(value, ParseTreeNode):
            result = self.results.get(id(value))
            if isinstance(result, SemanticValue):
                return result
            location = self.location_of(value)
            return SemanticValue(UNKNOWN, location=location)
        try:
            name = self.text_of(value)
        except ValueError:
            return SemanticValue(UNKNOWN, location=SourceLocation(1, 1))
        symbol = self.symbol_table.resolve(name)
        return self.value_of(symbol) if symbol is not None else SemanticValue(UNKNOWN)

    def symbol_of(self, value: object) -> Symbol | None:
        """Resolve a selected declaration reference without emitting errors."""
        if isinstance(value, Symbol):
            return value
        if isinstance(value, SemanticValue) and isinstance(value.symbol, Symbol):
            return value.symbol
        try:
            return self.symbol_table.resolve(self.text_of(value))
        except ValueError:
            return None


class SemanticEvaluator:
    """Traverse manual trees using only profile data and registered actions."""

    def __init__(
        self,
        registry: ActionRegistry | None = None,
        source_path: str | None = None,
    ) -> None:
        self.registry = registry or _default_registry()
        self.source_path = source_path
        self.context = SemanticContext(source_path=source_path)
        self._profile: SemanticProfile | None = None
        self._statistics = {"rules_visited": 0, "actions_executed": 0}

    def analyze(
        self,
        tree: ParseTreeNode,
        profile: SemanticProfile,
    ) -> SemanticAnalysisResult:
        """Analyze one tree and always restore scopes and contextual stacks."""
        self.context = SemanticContext(source_path=self.source_path)
        self._profile = profile
        self._statistics = {"rules_visited": 0, "actions_executed": 0}
        result: object = None
        try:
            result = self.visit(tree)
        finally:
            self.context.symbol_table.restore_global()
            self.context.function_stack.clear()
            self.context.class_stack.clear()
            self.context.loop_stack.clear()
            self._profile = None
        return SemanticAnalysisResult(
            diagnostics=self.context.diagnostics.items,
            symbol_table=self.context.symbol_table,
            value=result if isinstance(result, SemanticValue) else None,
            statistics=self._statistics,
        )

    def visit(self, node: ParseTreeNode) -> object:
        """Run entry actions, visit children in source order, then exit actions."""
        if self._profile is None:
            raise RuntimeError("visit requires an active analyze call")
        self._statistics["rules_visited"] += 1
        binding = resolve_binding(node, self._profile)
        scope_at_entry = self.context.symbol_table.current_scope
        function_depth = len(self.context.function_stack)
        class_depth = len(self.context.class_stack)
        loop_depth = len(self.context.loop_stack)
        result: object = None
        try:
            if binding is not None:
                for action in binding.actions:
                    if action.phase == "enter":
                        produced = self.invoke(action, node)
                        if produced is not None:
                            result = produced
            child_results = self.visit_children(node)
            if result is None and len(child_results) == 1:
                result = child_results[0]
            if binding is not None:
                for action in binding.actions:
                    if action.phase == "exit":
                        produced = self.invoke(action, node)
                        if produced is not None:
                            result = produced
            self.context.results[id(node)] = result
            return result
        finally:
            self._restore_node_context(
                scope_at_entry, function_depth, class_depth, loop_depth
            )

    def visit_children(self, node: ParseTreeNode) -> tuple[object, ...]:
        """Visit direct children from left to right."""
        return tuple(self.visit(child) for child in node.children)

    def select(self, node: ParseTreeNode, selector: ChildSelector) -> object:
        """Resolve one validated selector against the current node."""
        if selector.kind == "child":
            assert selector.index is not None
            try:
                child = node.children[selector.index]
            except IndexError as exc:
                raise ProfileError(
                    f"child index {selector.index} is out of range for "
                    f"{node.rule_name or node.symbol}"
                ) from exc
            return self.context.results.get(id(child))
        if selector.kind == "children":
            return tuple(self.context.results.get(id(child)) for child in node.children)
        if selector.kind == "token":
            for child in node.children:
                if child.token_type == selector.token:
                    return child
            raise ProfileError(
                f"token {selector.token!r} is not a direct child of "
                f"{node.rule_name or node.symbol}"
            )
        if selector.kind == "text":
            if node.text is not None:
                return node.text
            return "".join(_tree_text(child) for child in node.children)
        if selector.kind == "position":
            return self.context.location_of(node)
        raise ProfileError(f"unsupported selector: {selector.kind}")

    def invoke(self, action: ActionInvocation, node: ParseTreeNode) -> object:
        """Resolve arguments and call one allow-listed action."""
        handler = self.registry.resolve(action.name)
        arguments = {
            name: self.select(node, value) if isinstance(value, ChildSelector) else value
            for name, value in action.arguments.items()
        }
        self._statistics["actions_executed"] += 1
        return handler(self.context, node, **arguments)

    def _restore_node_context(
        self,
        scope_at_entry: object,
        function_depth: int,
        class_depth: int,
        loop_depth: int,
    ) -> None:
        while self.context.symbol_table.current_scope is not scope_at_entry:
            current = self.context.symbol_table.current_scope
            if current.parent is None:
                raise ProfileError("an action exited beyond its owning scope")
            self.context.symbol_table.exit_scope()
        del self.context.function_stack[function_depth:]
        del self.context.class_stack[class_depth:]
        del self.context.loop_stack[loop_depth:]


def _default_registry() -> ActionRegistry:
    registry = register_builtin_actions(ActionRegistry())
    registry.register("expression.literal", _literal)
    registry.register("expression.unary", _unary)
    registry.register("expression.binary", _binary)
    registry.register("expression.assignment", _assignment)
    registry.register("expression.ternary", _ternary)
    registry.register("expression.array", _array)
    registry.register("expression.index", _index)
    return registry


def _literal(
    context: SemanticContext,
    node: ParseTreeNode,
    kind: str,
    text: str | None = None,
) -> SemanticValue:
    return context.expressions.literal(
        kind, text if text is not None else context.text_of(node), context.location_of(node)
    )


def _unary(
    context: SemanticContext,
    node: ParseTreeNode,
    operator: str,
    operand: SemanticValue,
) -> SemanticValue:
    return context.expressions.unary(operator, operand, context.location_of(node))


def _binary(
    context: SemanticContext,
    node: ParseTreeNode,
    operator: str,
    left: SemanticValue,
    right: SemanticValue,
) -> SemanticValue:
    return context.expressions.binary(operator, left, right, context.location_of(node))


def _assignment(
    context: SemanticContext,
    node: ParseTreeNode,
    target: SemanticValue,
    value: SemanticValue,
) -> SemanticValue:
    return context.expressions.assignment(target, value, context.location_of(node))


def _ternary(
    context: SemanticContext,
    node: ParseTreeNode,
    condition: SemanticValue,
    true_value: SemanticValue,
    false_value: SemanticValue,
) -> SemanticValue:
    return context.expressions.ternary(
        condition, true_value, false_value, context.location_of(node)
    )


def _array(
    context: SemanticContext,
    node: ParseTreeNode,
    elements: tuple[SemanticValue, ...],
) -> SemanticValue:
    return context.expressions.array_literal(elements, context.location_of(node))


def _index(
    context: SemanticContext,
    node: ParseTreeNode,
    container: SemanticValue,
    index: SemanticValue,
) -> SemanticValue:
    return context.expressions.index(container, index, context.location_of(node))


def _positive_or_none(value: object) -> int | None:
    if value is None:
        return None
    return max(int(value), 1)


def _tree_text(node: ParseTreeNode) -> str:
    if node.text is not None:
        return node.text
    return "".join(_tree_text(child) for child in node.children)
