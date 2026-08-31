import pytest

from src.parser.parse_tree import ParseTreeNode
from src.semantic.action_registry import ActionRegistry
from src.semantic.evaluator import SemanticEvaluator
from src.semantic.profile import ActionInvocation, ChildSelector, RuleBinding, SemanticProfile
from src.semantic.symbol_table import ScopeKind
from src.semantic.types import INTEGER


def node(rule: str, text: str | None = None, children=()):
    return ParseTreeNode(rule, list(children), rule_name=rule, text=text, line=1, column=1)


def literal_profile(rule: str) -> SemanticProfile:
    return SemanticProfile(
        rule,
        (
            RuleBinding(
                rule,
                (
                    ActionInvocation(
                        "expression.literal",
                        {"kind": "integer", "text": ChildSelector("text")},
                    ),
                ),
            ),
        ),
    )


def test_evaluator_produces_a_typed_value_and_immutable_result():
    result = SemanticEvaluator().analyze(node("number", "42"), literal_profile("number"))
    assert result.accepted
    assert result.value.type == INTEGER
    assert result.value.constant_value == 42
    assert result.statistics == {"rules_visited": 1, "actions_executed": 1}


def test_two_rule_names_use_the_same_registered_action_without_python_changes():
    evaluator = SemanticEvaluator()
    first = evaluator.analyze(node("number", "1"), literal_profile("number"))
    second = evaluator.analyze(node("entero", "2"), literal_profile("entero"))
    assert (first.value.constant_value, second.value.constant_value) == (1, 2)


def test_manual_tree_produces_diagnostics_and_a_retained_symbol_table():
    number_binding = literal_profile("number").bindings[0]
    declaration_binding = RuleBinding(
        "declaration",
        (
            ActionInvocation(
                "declare.variable",
                {
                    "name": "value",
                    "type_": "integer",
                    "initializer": ChildSelector("child", index=0),
                },
            ),
        ),
    )
    profile = SemanticProfile("manual", (number_binding, declaration_binding))
    tree = node(
        "root",
        children=(
            node("declaration", children=(node("number", "1"),)),
            node("declaration", children=(node("number", "2"),)),
        ),
    )
    result = SemanticEvaluator().analyze(tree, profile)
    assert not result.accepted
    assert "already declared" in result.diagnostics[0].message
    assert [item.name for item in result.symbol_table.global_scope.symbols] == ["value"]


def test_evaluator_visits_children_left_to_right_between_enter_and_exit_actions():
    events = []
    registry = ActionRegistry()
    registry.register("enter", lambda context, current: events.append("enter"))
    registry.register("leaf", lambda context, current: events.append(current.text))
    registry.register("exit", lambda context, current: events.append("exit"))
    profile = SemanticProfile(
        "order",
        (
            RuleBinding(
                "root",
                (ActionInvocation("enter", phase="enter"), ActionInvocation("exit")),
            ),
            RuleBinding("leaf", (ActionInvocation("leaf"),)),
        ),
    )
    tree = node("root", children=(node("leaf", "a"), node("leaf", "b")))
    SemanticEvaluator(registry).analyze(tree, profile)
    assert events == ["enter", "a", "b", "exit"]


def test_evaluator_restores_context_when_an_action_raises():
    registry = ActionRegistry()
    registry.register(
        "open", lambda context, current: context.symbol_table.enter_scope(
            ScopeKind.BLOCK,
            "temporary",
            context.location_of(current),
        )
    )
    registry.register(
        "boom",
        lambda context, current: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    profile = SemanticProfile(
        "failure",
        (
            RuleBinding(
                "root",
                (ActionInvocation("open", phase="enter"), ActionInvocation("boom")),
            ),
        ),
    )
    evaluator = SemanticEvaluator(registry)
    with pytest.raises(RuntimeError, match="boom"):
        evaluator.analyze(node("root"), profile)
    assert (
        evaluator.context.symbol_table.current_scope
        is evaluator.context.symbol_table.global_scope
    )
    assert not evaluator.context.function_stack
    assert not evaluator.context.class_stack
    assert not evaluator.context.loop_stack
