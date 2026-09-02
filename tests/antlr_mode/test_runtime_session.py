from pathlib import Path

from src.antlr_mode.grammar_info import GrammarInfo
from src.antlr_mode.runner import (
    AntlrAnalysisResult,
    AntlrRuntimeSession,
)


def test_analysis_result_retains_an_opaque_runtime_session() -> None:
    native_tree = object()
    session = AntlrRuntimeSession(
        native_tree=native_tree,
        rule_names=("root", "expression"),
    )
    result = AntlrAnalysisResult(
        grammar=GrammarInfo(Path("MiniCalc.g4"), "MiniCalc", "combined", ("root",)),
        start_rule="root",
        tree=None,
        diagnostics=[],
        tokens=[],
        generated_directory=Path("output/antlr/generated/MiniCalc-test"),
        runtime_session=session,
    )

    assert result.native_tree is native_tree
    assert result.rule_names == ("root", "expression")
