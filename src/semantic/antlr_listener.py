"""Generic ANTLR listener that drives the parser-independent evaluator."""

from __future__ import annotations

from dataclasses import dataclass

from antlr4 import ParseTreeListener

from src.parser.parse_tree import ParseTreeNode
from src.semantic.diagnostics import DiagnosticCategory
from src.semantic.evaluator import SemanticEvaluator
from src.semantic.profile import RuleBinding, SemanticProfile, resolve_binding
from src.semantic.results import SemanticAnalysisResult
from src.semantic.values import SemanticValue


class SemanticListenerError(RuntimeError):
    """Report an incompatible native/common tree pair or invalid walk order."""


@dataclass(slots=True)
class _RuleFrame:
    native_node: object
    common_node: ParseTreeNode
    binding: RuleBinding | None
    scope_at_entry: object
    function_depth: int
    class_depth: int
    loop_depth: int
    result: object = None


class SemanticTreeListener(ParseTreeListener):
    """Execute declarative semantic actions from real ANTLR walk events."""

    def __init__(
        self,
        native_tree: object,
        common_tree: ParseTreeNode,
        rule_names: tuple[str, ...],
        profile: SemanticProfile,
        *,
        source_path: str | None = None,
        evaluator: SemanticEvaluator | None = None,
    ) -> None:
        super().__init__()
        self.profile = profile
        self.rule_names = tuple(rule_names)
        self.evaluator = evaluator or SemanticEvaluator(source_path=source_path)
        self._common_by_native_id: dict[int, ParseTreeNode] = {}
        self._frames: list[_RuleFrame] = []
        self._root_result: object = None
        self._statistics = {
            "rules_visited": 0,
            "actions_executed": 0,
            "terminals_visited": 0,
        }
        self._index_tree(native_tree, common_tree)

    def enterEveryRule(self, ctx: object) -> None:  # noqa: N802 - ANTLR API
        """Run configured entry actions for one parser-rule context."""
        common_node = self._common_node(ctx)
        rule_index = int(ctx.getRuleIndex())
        if not 0 <= rule_index < len(self.rule_names):
            raise SemanticListenerError(f"invalid ANTLR rule index: {rule_index}")
        expected_rule = self.rule_names[rule_index]
        if common_node.rule_name != expected_rule:
            raise SemanticListenerError(
                "native/common tree rule mismatch: "
                f"expected {expected_rule!r}, got {common_node.rule_name!r}"
            )

        context = self.evaluator.context
        frame = _RuleFrame(
            native_node=ctx,
            common_node=common_node,
            binding=resolve_binding(common_node, self.profile),
            scope_at_entry=context.symbol_table.current_scope,
            function_depth=len(context.function_stack),
            class_depth=len(context.class_stack),
            loop_depth=len(context.loop_stack),
        )
        self._frames.append(frame)
        self._statistics["rules_visited"] += 1
        if frame.binding is not None:
            for action in frame.binding.actions:
                if action.phase == "enter":
                    produced = self._invoke(action, common_node)
                    if produced is not None:
                        frame.result = produced

    def exitEveryRule(self, ctx: object) -> None:  # noqa: N802 - ANTLR API
        """Run exit actions after every child result is available."""
        if not self._frames or self._frames[-1].native_node is not ctx:
            raise SemanticListenerError(
                "ANTLR rule exit order does not match entry order"
            )
        frame = self._frames.pop()
        context = self.evaluator.context
        try:
            child_results = tuple(
                context.results.get(id(child)) for child in frame.common_node.children
            )
            meaningful_results = tuple(
                result for result in child_results if result is not None
            )
            if frame.result is None and len(meaningful_results) == 1:
                frame.result = meaningful_results[0]
            if frame.binding is not None:
                for action in frame.binding.actions:
                    if action.phase == "exit":
                        produced = self._invoke(action, frame.common_node)
                        if produced is not None:
                            frame.result = produced
            context.results[id(frame.common_node)] = frame.result
            if not self._frames:
                self._root_result = frame.result
        finally:
            self._restore_context(frame)

    def visitTerminal(self, node: object) -> None:  # noqa: N802 - ANTLR API
        """Retain the terminal's precomputed common-tree metadata."""
        common_node = self._common_node(node)
        self.evaluator.context.results[id(common_node)] = None
        self._statistics["terminals_visited"] += 1

    def visitErrorNode(self, node: object) -> None:  # noqa: N802 - ANTLR API
        """Convert an unexpected ANTLR error node into a semantic diagnostic."""
        common_node = self._common_node(node)
        text = common_node.text or common_node.symbol
        self.evaluator.context.diagnostics.add(
            DiagnosticCategory.GENERAL,
            f"ANTLR error node encountered during semantic traversal: {text!r}",
            self.evaluator.context.location_of(common_node),
        )
        self.evaluator.context.results[id(common_node)] = None
        self._statistics["terminals_visited"] += 1

    @property
    def result(self) -> SemanticAnalysisResult:
        """Return the semantic result accumulated by a completed tree walk."""
        if self._frames:
            raise SemanticListenerError(
                "semantic result requested before walk completed"
            )
        context = self.evaluator.context
        return SemanticAnalysisResult(
            diagnostics=context.diagnostics.items,
            symbol_table=context.symbol_table,
            value=(
                self._root_result
                if isinstance(self._root_result, SemanticValue)
                else None
            ),
            statistics=self._statistics,
        )

    def abort(self) -> None:
        """Restore evaluator state after a walker or profile failure."""
        context = self.evaluator.context
        context.symbol_table.restore_global()
        context.function_stack.clear()
        context.class_stack.clear()
        context.loop_stack.clear()
        self._frames.clear()

    def _invoke(self, action, node: ParseTreeNode) -> object:
        self._statistics["actions_executed"] += 1
        return self.evaluator.invoke(action, node)

    def _common_node(self, native_node: object) -> ParseTreeNode:
        try:
            return self._common_by_native_id[id(native_node)]
        except KeyError as exc:
            raise SemanticListenerError(
                "ANTLR walker produced a node absent from the common tree"
            ) from exc

    def _index_tree(self, native_node: object, common_node: ParseTreeNode) -> None:
        self._common_by_native_id[id(native_node)] = common_node
        native_count = int(native_node.getChildCount())
        if native_count != len(common_node.children):
            raise SemanticListenerError(
                "native/common tree child-count mismatch for "
                f"{common_node.rule_name or common_node.symbol!r}: "
                f"{native_count} != {len(common_node.children)}"
            )
        for index, child in enumerate(common_node.children):
            self._index_tree(native_node.getChild(index), child)

    def _restore_context(self, frame: _RuleFrame) -> None:
        context = self.evaluator.context
        while context.symbol_table.current_scope is not frame.scope_at_entry:
            current = context.symbol_table.current_scope
            if current.parent is None:
                raise SemanticListenerError("an action exited beyond its owning scope")
            context.symbol_table.exit_scope()
        del context.function_stack[frame.function_depth:]
        del context.class_stack[frame.class_depth:]
        del context.loop_stack[frame.loop_depth:]
