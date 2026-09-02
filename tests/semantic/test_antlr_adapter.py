import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from src.antlr_mode.grammar_info import GrammarInfo
from src.antlr_mode.runner import (
    AntlrAnalysisResult,
    AntlrDiagnostic,
    AntlrRuntimeSession,
)
from src.parser.parse_tree import ParseTreeNode
from src.semantic.types import INTEGER


def _load_adapter_module():
    import src.semantic.antlr_adapter as adapter
    return adapter


@contextmanager
def _patched_walker() -> Iterator[None]:
    previous_module = sys.modules.get("antlr4")
    try:
        import antlr4 as antlr_module
    except ModuleNotFoundError:
        antlr_module = ModuleType("antlr4")

        class ParseTreeListener:
            pass

        antlr_module.ParseTreeListener = ParseTreeListener
        sys.modules["antlr4"] = antlr_module
    missing = object()
    previous_walker = getattr(antlr_module, "ParseTreeWalker", missing)
    antlr_module.ParseTreeWalker = type(
        "ParseTreeWalker",
        (),
        {"DEFAULT": _Walker()},
    )
    try:
        yield
    finally:
        if previous_walker is missing:
            del antlr_module.ParseTreeWalker
        else:
            antlr_module.ParseTreeWalker = previous_walker
        if previous_module is None:
            sys.modules.pop("antlr4", None)
            sys.modules.pop("src.semantic.antlr_listener", None)


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
    def __init__(self, children: list[object]) -> None:
        self.children = children
        self.start = children[0].symbol if children else _Token("")
        self.stop = self.start

    def getRuleIndex(self) -> int:
        return 0

    def getChildCount(self) -> int:
        return len(self.children)

    def getChild(self, index: int) -> object:
        return self.children[index]


class _Walker:
    def walk(self, listener, node: object) -> None:
        if hasattr(node, "getRuleIndex"):
            listener.enterEveryRule(node)
            for child in node.children:
                self.walk(listener, child)
            listener.exitEveryRule(node)
        else:
            listener.visitTerminal(node)


def test_adapter_skips_semantics_when_syntax_is_rejected() -> None:
    adapter = _load_adapter_module()
    syntax_result = AntlrAnalysisResult(
        grammar=GrammarInfo(
            Path("Broken.g4"),
            "Broken",
            "combined",
            ("root",),
        ),
        start_rule="root",
        tree=None,
        diagnostics=[AntlrDiagnostic("PARSER", 1, 1, "missing expression")],
        tokens=[],
        generated_directory=Path("output/antlr/generated/Broken-test"),
    )
    original_analyze = adapter.analyze_with_g4
    adapter.analyze_with_g4 = lambda *args, **kwargs: syntax_result
    try:
        result = adapter.analyze_semantics_with_g4(
            "Broken.g4",
            "let = ;",
            "profile-that-must-not-be-read.json",
            start_rule="root",
            source_path="broken.cps",
        )
    finally:
        adapter.analyze_with_g4 = original_analyze

    assert result.syntax_result is syntax_result
    assert result.semantic_result is None
    assert not result.accepted


def test_adapter_walks_an_accepted_tree_and_propagates_source_path() -> None:
    adapter = _load_adapter_module()
    terminal = _Terminal("7")
    native_tree = _Rule([terminal])
    common_tree = ParseTreeNode(
        "expression",
        [ParseTreeNode("7", token_type="INTEGER", text="7", line=1, column=1)],
        rule_name="expression",
        alternative="IntegerExpression",
        line=1,
        column=1,
    )
    syntax_result = AntlrAnalysisResult(
        grammar=GrammarInfo(
            Path("MiniCalc.g4"),
            "MiniCalc",
            "combined",
            ("expression",),
        ),
        start_rule="expression",
        tree=common_tree,
        diagnostics=[],
        tokens=[],
        generated_directory=Path("output/antlr/generated/MiniCalc-test"),
        runtime_session=AntlrRuntimeSession(native_tree, ("expression",)),
    )
    original_analyze = adapter.analyze_with_g4
    adapter.analyze_with_g4 = lambda *args, **kwargs: syntax_result
    try:
        with _patched_walker():
            result = adapter.analyze_semantics_with_g4(
                "MiniCalc.g4",
                "7",
                Path("tests/semantic/fixtures/literal.semantic.json"),
                start_rule="expression",
                source_path="example.mc",
            )
    finally:
        adapter.analyze_with_g4 = original_analyze

    assert result.accepted
    assert result.semantic_result is not None
    assert result.semantic_result.value is not None
    assert result.semantic_result.value.type == INTEGER
    assert result.semantic_result.value.location is not None
    assert result.semantic_result.value.location.source_path == "example.mc"


def test_adapter_wraps_incompatible_tree_errors() -> None:
    adapter = _load_adapter_module()
    native_tree = _Rule([])
    common_tree = ParseTreeNode(
        "expression",
        [ParseTreeNode("7", token_type="INTEGER", text="7")],
        rule_name="expression",
        alternative="IntegerExpression",
    )
    syntax_result = AntlrAnalysisResult(
        grammar=GrammarInfo(
            Path("MiniCalc.g4"),
            "MiniCalc",
            "combined",
            ("expression",),
        ),
        start_rule="expression",
        tree=common_tree,
        diagnostics=[],
        tokens=[],
        generated_directory=Path("output/antlr/generated/MiniCalc-test"),
        runtime_session=AntlrRuntimeSession(native_tree, ("expression",)),
    )
    original_analyze = adapter.analyze_with_g4
    adapter.analyze_with_g4 = lambda *args, **kwargs: syntax_result
    try:
        with _patched_walker():
            try:
                adapter.analyze_semantics_with_g4(
                    "MiniCalc.g4",
                    "7",
                    Path("tests/semantic/fixtures/literal.semantic.json"),
                )
            except adapter.SemanticAdapterError as exc:
                assert "semantic traversal failed" in str(exc)
            else:
                raise AssertionError("expected SemanticAdapterError")
    finally:
        adapter.analyze_with_g4 = original_analyze


def test_adapter_rejects_profile_for_a_different_grammar() -> None:
    adapter = _load_adapter_module()
    terminal = _Terminal("7")
    native_tree = _Rule([terminal])
    common_tree = ParseTreeNode(
        "expression",
        [ParseTreeNode("7", token_type="INTEGER", text="7")],
        rule_name="expression",
        alternative="IntegerExpression",
    )
    syntax_result = AntlrAnalysisResult(
        grammar=GrammarInfo(
            Path("MiniCalc.g4"),
            "MiniCalc",
            "combined",
            ("expression",),
        ),
        start_rule="expression",
        tree=common_tree,
        diagnostics=[],
        tokens=[],
        generated_directory=Path("output/antlr/generated/MiniCalc-test"),
        runtime_session=AntlrRuntimeSession(native_tree, ("expression",)),
    )
    original_analyze = adapter.analyze_with_g4
    adapter.analyze_with_g4 = lambda *args, **kwargs: syntax_result
    try:
        try:
            adapter.analyze_semantics_with_g4(
                "MiniCalc.g4",
                "7",
                Path("tests/semantic/fixtures/incompatible.semantic.json"),
            )
        except adapter.SemanticAdapterError as exc:
            assert "invalid semantic profile" in str(exc)
            assert "declaration" in str(exc)
        else:
            raise AssertionError("expected SemanticAdapterError")
    finally:
        adapter.analyze_with_g4 = original_analyze
