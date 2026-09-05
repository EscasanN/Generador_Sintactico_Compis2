"""Extra grammar-neutral actions and orchestration needed by block 4.

Blocks 1-3 froze a generic semantic engine driven entirely by declarative
JSON profiles. Their selector language (``src/semantic/profile.py``) can only
read a *fixed* child index, a direct terminal by token type, the whole
node's concatenated text, or every direct child at once. It has no way to
flatten a variable-length comma list, filter interspersed separators, or
thread one action's result into a sibling action's argument.

While building ``semantic_profiles/compiscript.semantic.json`` against the
real official grammar, two genuine, grammar-neutral gaps showed up that no
combination of published selectors and published actions could close:

- ``function.call``/``expression.array``/``function.declare`` all need a
  clean ``tuple[SemanticValue, ...]`` built from a comma-separated list
  (call arguments, array elements, typed parameter lists). The only
  selector able to reach every element at once (``children``) also returns
  the separators, and nothing filters or accumulates them into one value
  across the recursive comma chain.
- A few statement forms need to *compose* two already-published actions in
  sequence on the same node (resolve an identifier or a member access, then
  validate the assignment against it). Profiles cannot chain two actions on
  one node because a selector only ever reads a *child's* stored result,
  never a sibling action's output.

Nothing here reimplements Daniel's, Nadissa's or Dulce's logic: every
function below only *composes* or *feeds* the real published functions
(``ExpressionActions``, ``resolve_identifier``, ``access_member``,
``declare_function``, ``declare_method``). They are grammar-neutral (no
Compiscript name appears in this module) and safe (no ``eval``/``exec``,
pure Python, deterministic). They are registered under an ``x.`` namespace
so any profile using them is trivially auditable.

This module also exposes :func:`analyze_semantics_with_extensions`, a thin
wrapper that mirrors ``src.semantic.antlr_adapter.analyze_semantics_with_g4``
but injects an :class:`~src.semantic.action_registry.ActionRegistry` that
includes these extra actions. It reuses Dulce's own public building blocks
(``analyze_with_g4``, ``load_profile``, ``validate_profile``,
``SemanticTreeListener``, ``SemanticEvaluator``, ``ParseTreeWalker``)
unchanged; it does not alter any file owned by a previous block.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from types import SimpleNamespace

from src.antlr_mode.runner import AntlrAnalysisResult, analyze_with_g4
from src.semantic.action_registry import ActionRegistry
from src.semantic.actions.callables import declare_function
from src.semantic.actions.classes import access_member, declare_method
from src.semantic.actions.control_flow import validate_sequence
from src.semantic.actions.declarations import resolve_identifier
from src.semantic.evaluator import SemanticContext, SemanticEvaluator
from src.semantic.profile import ProfileError, load_profile, validate_profile
from src.semantic.results import SemanticAnalysisResult
from src.semantic.types import VOID, Type
from src.semantic.values import SemanticValue


# ---------------------------------------------------------------------------
# Generic list/pair helpers for comma-separated grammar constructs.
# ---------------------------------------------------------------------------


def start_list(context: SemanticContext, node: Any, first: Any = None) -> tuple[Any, ...]:
    """Wrap the first element of a comma list into a one-item tuple."""
    del context, node
    return (first,)


def append_list(
    context: SemanticContext,
    node: Any,
    previous: Any = (),
    next: Any = None,
) -> tuple[Any, ...]:
    """Append one more element to a comma list accumulated left to right."""
    del context, node
    return tuple(previous) + (next,)


def _concatenated_text(node: Any) -> str:
    """Join every descendant terminal's text, mirroring the ``text`` selector.

    ``SemanticContext.text_of`` is meant for leaves, symbols and already
    resolved values, not for concatenating an entire non-terminal subtree
    (a ``type`` node has no ``.text`` of its own; it is a rule node made of
    a ``baseType`` terminal plus optional ``[]`` pairs). This local helper
    reproduces the same tiny recursive join that
    ``src.semantic.evaluator``'s private ``text`` selector already performs,
    without depending on that module's non-public helper.
    """
    text = getattr(node, "text", None)
    if text is not None:
        return str(text)
    children = getattr(node, "children", ())
    return "".join(_concatenated_text(child) for child in children)


def node_text(context: SemanticContext, node: Any) -> str:
    """Return the current node's own concatenated source text.

    Used to read a ``type`` node (``baseType`` plus any ``[]`` suffixes) as
    a plain string such as ``"integer"`` or ``"integer[]"``, which
    :func:`src.semantic.types.type_from_name` already knows how to parse.
    """
    del context
    return _concatenated_text(node)


def build_array(
    context: SemanticContext,
    node: Any,
    elements: Iterable[SemanticValue] = (),
) -> SemanticValue:
    """Build an array literal from an already-clean tuple of elements.

    Delegates entirely to Daniel's ``ExpressionActions.array_literal``; this
    wrapper only supplies a safe default so an empty ``[]`` literal (with no
    comma-list child at all) does not need an unsupported empty-list JSON
    argument.
    """
    return context.expressions.array_literal(tuple(elements), context.location_of(node))


def assign_to_identifier(
    context: SemanticContext,
    node: Any,
    name: Any,
    value: SemanticValue,
) -> SemanticValue:
    """Resolve a bare identifier target, then validate the assignment.

    Composes Nadissa's ``resolve_identifier`` with Daniel's
    ``ExpressionActions.assignment`` for the top-level ``Identifier '='
    expression ';'`` statement, which (unlike expression-level assignments)
    does not route the target through ``leftHandSide``.
    """
    target = resolve_identifier(context, node, name)
    return context.expressions.assignment(target, value, context.location_of(node))


def assign_to_member(
    context: SemanticContext,
    node: Any,
    instance: SemanticValue,
    name: Any,
    value: SemanticValue,
) -> SemanticValue:
    """Resolve a ``instance.member`` target, then validate the assignment.

    Composes Nadissa's ``access_member`` with Daniel's
    ``ExpressionActions.assignment`` for the top-level
    ``expression '.' Identifier '=' expression ';'`` statement.
    """
    target = access_member(context, node, instance, name)
    return context.expressions.assignment(target, value, context.location_of(node))


def _find_child_by_rule(node: Any, rule_name: str) -> Any | None:
    """Return the first direct child whose ``rule_name`` matches, if any."""
    for child in getattr(node, "children", ()):
        if getattr(child, "rule_name", None) == rule_name:
            return child
    return None


def _find_child_by_token(node: Any, token_type: str) -> Any | None:
    """Return the first direct child whose ``token_type`` matches, if any."""
    for child in getattr(node, "children", ()):
        if getattr(child, "token_type", None) == token_type:
            return child
    return None


def _collect_parameter_pairs(parameters_node: Any) -> tuple[tuple[str, str | None], ...]:
    """Walk a (possibly left-recursive) ``parameters`` subtree into pairs.

    ``function.declare``/``function.enter`` must run at the *enter* phase of
    ``functionDeclaration`` -- before its ``block`` body is visited -- so a
    recursive call inside the body resolves the function's own name. But
    that means the sibling ``parameters``/``type`` children have not been
    semantically visited yet, so their computed values (what a ``child``
    selector would return) are not in ``context.results`` at that point.
    Parameter names and type annotations are pure source text, though --
    they never needed a semantic value -- so this walks the already-built
    syntax subtree directly instead of reading a not-yet-populated result.
    """
    if parameters_node is None:
        return ()
    if parameters_node.alternative == "MoreParameters":
        previous = _collect_parameter_pairs(parameters_node.children[0])
        return previous + (_parameter_pair(parameters_node.children[2]),)
    # FirstParameter: single child is the "parameter" node itself.
    return (_parameter_pair(parameters_node.children[0]),)


def _parameter_pair(parameter_node: Any) -> tuple[str, str | None]:
    """Extract ``(name, type_text_or_None)`` from one ``parameter`` node."""
    identifier = _find_child_by_token(parameter_node, "Identifier")
    name = identifier.text if identifier is not None else ""
    type_node = _find_child_by_rule(parameter_node, "type")
    type_text = _concatenated_text(type_node) if type_node is not None else None
    return (name, type_text)


def declare_function_with_pairs(
    context: SemanticContext,
    node: Any,
    name: Any,
) -> SemanticValue:
    """Declare a function, reading its parameters/return type from the tree.

    Delegates entirely to the real, published ``declare_function``; this
    wrapper only supplies the ``parameter_types``/``parameter_names``/
    ``return_type`` arguments it needs, extracted via
    :func:`_collect_parameter_pairs` (see that function's docstring for why
    a selector cannot supply them here).
    """
    parameters_node = _find_child_by_rule(node, "parameters")
    type_node = _find_child_by_rule(node, "type")
    pairs = _collect_parameter_pairs(parameters_node)
    names = tuple(pair[0] for pair in pairs)
    types = tuple(pair[1] for pair in pairs)
    return_type = _concatenated_text(type_node) if type_node is not None else VOID
    return declare_function(context, node, name, types, return_type, names)


def declare_method_with_pairs(
    context: SemanticContext,
    node: Any,
    name: Any,
) -> SemanticValue:
    """Declare a method, reading its parameters/return type from the tree.

    Same rationale and technique as :func:`declare_function_with_pairs`,
    delegating to the real, published ``declare_method``.
    """
    parameters_node = _find_child_by_rule(node, "parameters")
    type_node = _find_child_by_rule(node, "type")
    pairs = _collect_parameter_pairs(parameters_node)
    names = tuple(pair[0] for pair in pairs)
    types = tuple(pair[1] for pair in pairs)
    return_type = _concatenated_text(type_node) if type_node is not None else VOID
    return declare_method(context, node, name, types, return_type, names)


def sequence_trimmed(
    context: SemanticContext,
    node: Any,
    statements: Iterable[Any] = (),
    skip_start: int = 0,
    skip_end: int = 0,
) -> Any:
    """Run dead-code detection over a statement list, minus its punctuation.

    ``control.sequence`` (``validate_sequence``) is a generic, already-safe
    fold over "every child of this node" -- it never crashes on ``None``
    entries, but it also never distinguishes an actual statement from a
    structural terminal that merely sits at the same sibling level (a
    block's own ``{``/``}``, a switch case's ``case``/``:``). Once a
    ``return``/``break``/``continue`` sets its "unreachable from here on"
    flag, the very next sibling -- even a closing brace -- gets flagged as
    dead code. This wrapper trims exactly the known-fixed number of leading
    and/or trailing structural children (grammar-neutral: the caller states
    the counts) before delegating to the real, published
    ``validate_sequence``, keeping a matching ``node.children`` slice so its
    own indexing (used for diagnostic locations) still lines up.
    """
    values = tuple(statements)
    children = tuple(getattr(node, "children", ()))
    value_end = len(values) - skip_end if skip_end else len(values)
    child_end = len(children) - skip_end if skip_end else len(children)
    proxy = SimpleNamespace(children=children[skip_start:child_end])
    return validate_sequence(context, proxy, values[skip_start:value_end])


def register_extended_actions(registry: ActionRegistry) -> ActionRegistry:
    """Register every ``x.*`` helper on top of the frozen builtin actions."""
    registry.register("x.list_start", start_list)
    registry.register("x.list_append", append_list)
    registry.register("x.text", node_text)
    registry.register("x.sequence", sequence_trimmed)
    registry.register("x.array", build_array)
    registry.register("x.assign_identifier", assign_to_identifier)
    registry.register("x.assign_member", assign_to_member)
    registry.register("x.declare_function", declare_function_with_pairs)
    registry.register("x.declare_method", declare_method_with_pairs)
    return registry


def default_extended_registry() -> ActionRegistry:
    """Build the default builtin registry plus every extension in this module."""
    return register_extended_actions(SemanticEvaluator().registry)


# ---------------------------------------------------------------------------
# Orchestration mirroring src.semantic.antlr_adapter.analyze_semantics_with_g4
# ---------------------------------------------------------------------------


class SemanticBridgeError(RuntimeError):
    """Report an invalid profile, unavailable runtime, or incompatible tree."""


@dataclass(frozen=True, slots=True)
class SemanticRunResult:
    """Bundle syntax and optional semantics, matching Dulce's adapter shape."""

    syntax_result: AntlrAnalysisResult
    semantic_result: SemanticAnalysisResult | None = None

    @property
    def accepted(self) -> bool:
        """Accept only when both frontend and semantic stages succeed."""
        return (
            self.syntax_result.accepted
            and self.semantic_result is not None
            and self.semantic_result.accepted
        )


def analyze_semantics_with_extensions(
    grammar_path: str | Path,
    source: str,
    profile_path: str | Path,
    start_rule: str | None = None,
    source_path: str | Path | None = None,
) -> SemanticRunResult:
    """Run syntax then semantics using the registry extended with ``x.*``.

    This mirrors ``analyze_semantics_with_g4`` step by step (inspect and run
    the grammar, stop on syntax errors, load and validate the profile, walk
    the native ANTLR tree with ``SemanticTreeListener`` and
    ``ParseTreeWalker.DEFAULT``) but constructs the evaluator with the
    extended action registry so ``x.*`` bindings resolve. It is grammar
    neutral: any profile that never references ``x.*`` behaves identically
    to calling Dulce's adapter directly.
    """
    syntax_result = analyze_with_g4(grammar_path, source, start_rule)
    if not syntax_result.accepted:
        return SemanticRunResult(syntax_result=syntax_result)
    if syntax_result.tree is None or syntax_result.native_tree is None:
        raise SemanticBridgeError(
            "ANTLR accepted the input but did not retain both tree representations"
        )
    if not syntax_result.rule_names:
        raise SemanticBridgeError(
            "ANTLR accepted the input but did not retain parser rule names"
        )

    try:
        profile = load_profile(profile_path)
        validate_profile(profile, syntax_result.grammar.parser_rules)
    except ProfileError as exc:
        raise SemanticBridgeError(f"invalid semantic profile: {exc}") from exc

    try:
        from antlr4 import ParseTreeWalker

        from src.semantic.antlr_listener import (
            SemanticListenerError,
            SemanticTreeListener,
        )
    except ImportError as exc:
        raise SemanticBridgeError(
            "antlr4-python3-runtime is required for semantic tree traversal"
        ) from exc

    resolved_source_path = str(source_path) if source_path is not None else None
    evaluator = SemanticEvaluator(
        registry=default_extended_registry(), source_path=resolved_source_path
    )
    listener = None
    try:
        listener = SemanticTreeListener(
            native_tree=syntax_result.native_tree,
            common_tree=syntax_result.tree,
            rule_names=syntax_result.rule_names,
            profile=profile,
            source_path=resolved_source_path,
            evaluator=evaluator,
        )
        ParseTreeWalker.DEFAULT.walk(listener, syntax_result.native_tree)
        semantic_result = listener.result
    except (ProfileError, SemanticListenerError) as exc:
        if listener is not None:
            listener.abort()
        raise SemanticBridgeError(f"semantic traversal failed: {exc}") from exc
    return SemanticRunResult(syntax_result=syntax_result, semantic_result=semantic_result)


__all__ = [
    "SemanticBridgeError",
    "SemanticRunResult",
    "analyze_semantics_with_extensions",
    "default_extended_registry",
    "register_extended_actions",
]
