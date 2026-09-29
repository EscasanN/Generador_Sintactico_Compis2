import json

import pytest

from src.antlr_mode.parse_tree import ParseTreeNode
from src.semantic.action_registry import ActionRegistry
from src.semantic.profile import (
    ActionInvocation,
    ChildSelector,
    ProfileError,
    RuleBinding,
    SemanticProfile,
    grammar_source_sha256,
    load_profile,
    resolve_binding,
    validate_profile,
    validate_profile_identity,
)


def test_load_profile_accepts_only_declarative_actions_and_selectors(tmp_path):
    path = tmp_path / "safe.json"
    path.write_text(
        json.dumps(
            {
                "name": "safe",
                "version": 1,
                "grammar": {
                    "name": "SafeGrammar",
                    "sha256": "0" * 64,
                },
                "bindings": [
                    {
                        "rule": "atom",
                        "actions": [
                            {
                                "name": "expression.literal",
                                "arguments": {
                                    "kind": "integer",
                                    "text": {"$select": "text"},
                                },
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile = load_profile(path)
    assert profile.name == "safe"
    assert profile.grammar_name == "SafeGrammar"
    assert profile.grammar_sha256 == "0" * 64
    assert profile.bindings[0].actions[0].arguments["text"] == ChildSelector("text")


@pytest.mark.parametrize(
    "payload",
    ["{", "[]", '{"name":"x","bindings":{}}', '{"name":"x","bindings":[],"extra":1}'],
)
def test_load_profile_rejects_invalid_json_or_schema(tmp_path, payload):
    path = tmp_path / "bad.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(path)


def test_validate_profile_reports_rules_absent_from_selected_grammar():
    profile = SemanticProfile("p", (RuleBinding("missing", (ActionInvocation("x"),)),))
    with pytest.raises(ProfileError, match="missing"):
        validate_profile(profile, {"present"})


def test_resolve_binding_prefers_labeled_alternative_then_rule():
    base = RuleBinding("expression", (ActionInvocation("base"),))
    special = RuleBinding("expression", (ActionInvocation("special"),), "Add")
    profile = SemanticProfile("p", (base, special))
    node = ParseTreeNode("expression", rule_name="expression", alternative="Add")
    assert resolve_binding(node, profile) is special
    node.alternative = "Other"
    assert resolve_binding(node, profile) is base


def test_action_registry_rejects_duplicate_and_unknown_names():
    registry = ActionRegistry()
    registry.register("known", lambda context, node: None)
    assert registry.names == ("known",)
    with pytest.raises(ProfileError):
        registry.register("known", lambda context, node: None)
    with pytest.raises(ProfileError, match="unknown"):
        registry.resolve("unknown")


@pytest.mark.parametrize(
    "selector",
    [
        lambda: ChildSelector("python"),
        lambda: ChildSelector("child", index=-1),
        lambda: ChildSelector("token"),
        lambda: ChildSelector("text", index=0),
    ],
)
def test_child_selector_rejects_unsafe_or_malformed_forms(selector):
    with pytest.raises(ProfileError):
        selector()


def test_after_child_phase_requires_a_non_negative_child_index():
    """A mid-rule action must identify exactly which completed child triggers it."""
    action = ActionInvocation("bind", phase="after_child", after_child=2)

    assert action.after_child == 2
    with pytest.raises(ProfileError, match="after_child"):
        ActionInvocation("bind", phase="after_child")
    with pytest.raises(ProfileError, match="after_child"):
        ActionInvocation("bind", phase="exit", after_child=0)


def test_profile_identity_checks_grammar_name_and_normalized_source(tmp_path):
    grammar = tmp_path / "Example.g4"
    grammar.write_text("grammar Example;\r\nroot: EOF;\r\n", encoding="utf-8")
    digest = grammar_source_sha256(grammar)
    binding = RuleBinding("root", (ActionInvocation("noop"),))
    compatible = SemanticProfile(
        "example",
        (binding,),
        grammar_name="Example",
        grammar_sha256=digest,
    )

    validate_profile_identity(compatible, "Example", grammar)

    with pytest.raises(ProfileError, match="name"):
        validate_profile_identity(compatible, "Other", grammar)
    incompatible = SemanticProfile(
        "example",
        (binding,),
        grammar_name="Example",
        grammar_sha256="0" * 64,
    )
    with pytest.raises(ProfileError, match="fingerprint"):
        validate_profile_identity(incompatible, "Example", grammar)
