import json

import pytest

from src.parser.parse_tree import ParseTreeNode
from src.semantic.action_registry import ActionRegistry
from src.semantic.profile import (
    ActionInvocation,
    ChildSelector,
    ProfileError,
    RuleBinding,
    SemanticProfile,
    load_profile,
    resolve_binding,
    validate_profile,
)


def test_load_profile_accepts_only_declarative_actions_and_selectors(tmp_path):
    path = tmp_path / "safe.json"
    path.write_text(
        json.dumps(
            {
                "name": "safe",
                "version": 1,
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
