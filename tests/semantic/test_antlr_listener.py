import sys
from types import ModuleType

from src.parser.parse_tree import ParseTreeNode
from src.semantic.profile import (
    ActionInvocation,
    ChildSelector,
    RuleBinding,
    SemanticProfile,
)
from src.semantic.types import INTEGER


def _load_listener_class():
    try:
        from src.semantic.antlr_listener import SemanticTreeListener
    except ModuleNotFoundError as exc:
        if exc.name != "antlr4":
            raise
        antlr_module = ModuleType("antlr4")

        class ParseTreeListener:
            pass

        antlr_module.ParseTreeListener = ParseTreeListener
        sys.modules["antlr4"] = antlr_module
        from src.semantic.antlr_listener import SemanticTreeListener
    return SemanticTreeListener


class _Token:
    def __init__(self, text: str) -> None:
        self.text = text
        self.line = 1
        self.column = 0


class _Terminal:
    def __init__(self, text: str) -> None:
        self.symbol = _Token(text)

    def getChildCount(self) -> int:
        return 0


class _Rule:
    def __init__(self, rule_index: int, children: list[object]) -> None:
        self._rule_index = rule_index
        self.children = children
        self.start = _Token(children[0].symbol.text)
        self.stop = self.start

    def getRuleIndex(self) -> int:
        return self._rule_index

    def getChildCount(self) -> int:
        return len(self.children)

    def getChild(self, index: int) -> object:
        return self.children[index]


def test_listener_executes_profile_actions_during_native_tree_events() -> None:
    SemanticTreeListener = _load_listener_class()
    terminal = _Terminal("42")
    native_tree = _Rule(0, [terminal])
    common_tree = ParseTreeNode(
        "expression",
        [
            ParseTreeNode(
                "42",
                token_type="INTEGER",
                text="42",
                line=1,
                column=1,
                end_line=1,
                end_column=2,
            )
        ],
        rule_name="expression",
        alternative="IntegerExpression",
        line=1,
        column=1,
        end_line=1,
        end_column=2,
    )
    profile = SemanticProfile(
        "MiniCalc",
        (
            RuleBinding(
                "expression",
                (
                    ActionInvocation(
                        "expression.literal",
                        {
                            "kind": "integer",
                            "text": ChildSelector("text"),
                        },
                    ),
                ),
                alternative="IntegerExpression",
            ),
        ),
    )
    listener = SemanticTreeListener(
        native_tree=native_tree,
        common_tree=common_tree,
        rule_names=("expression",),
        profile=profile,
    )

    listener.enterEveryRule(native_tree)
    listener.visitTerminal(terminal)
    listener.exitEveryRule(native_tree)

    assert listener.result.accepted
    assert listener.result.value is not None
    assert listener.result.value.type == INTEGER
    assert listener.result.value.constant_value == 42
    assert listener.result.statistics == {
        "rules_visited": 1,
        "actions_executed": 1,
        "terminals_visited": 1,
    }
