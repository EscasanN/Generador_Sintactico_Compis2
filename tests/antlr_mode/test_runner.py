from collections.abc import Iterator
from pathlib import Path

import pytest

from src.antlr_mode.runner import AntlrModeError, analyze_with_g4
from src.parser.parse_tree import ParseTreeNode


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPISCRIPT_GRAMMAR = (
    REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
)
MINI_CALC_GRAMMAR = Path(__file__).parent / "fixtures" / "MiniCalc.g4"


def test_compiscript_g4_accepts_valid_complete_program() -> None:
    result = analyze_with_g4(
        COMPISCRIPT_GRAMMAR,
        "let x: integer = 1; print(x);",
        "program",
    )

    assert result.accepted
    assert result.tree is not None
    assert result.tree.symbol == "program"
    assert result.tree.rule_name == "program"
    assert result.tree.line == 1
    assert result.native_tree is not None
    assert "program" in result.rule_names
    assert not result.diagnostics
    assert any(token.token_type == "Identifier" for token in result.tokens)
    assert any(
        node.is_leaf and node.line is not None and node.column is not None
        for node in _walk(result.tree)
    )


def test_compiscript_g4_collects_syntax_diagnostics() -> None:
    result = analyze_with_g4(
        COMPISCRIPT_GRAMMAR,
        "let x: integer = ;",
        "program",
    )

    assert not result.accepted
    assert result.diagnostics
    assert all(diagnostic.line >= 1 for diagnostic in result.diagnostics)
    assert all(diagnostic.column >= 1 for diagnostic in result.diagnostics)


def test_second_grammar_works_without_project_code_changes() -> None:
    result = analyze_with_g4(
        MINI_CALC_GRAMMAR,
        "10 + 20 - 5",
        "root",
    )

    assert result.accepted
    assert result.grammar.name == "MiniCalc"
    assert result.start_rule == "root"
    assert result.tree is not None
    assert result.tree.symbol == "root"


def test_reports_input_left_after_selected_start_rule() -> None:
    result = analyze_with_g4(
        COMPISCRIPT_GRAMMAR,
        "let first = 1; let second = 2;",
        "statement",
    )

    assert not result.accepted
    assert any(
        "antes del final de la entrada" in diagnostic.message
        for diagnostic in result.diagnostics
    )


def test_rejects_unknown_start_rule_before_generation() -> None:
    with pytest.raises(AntlrModeError, match="no existe"):
        analyze_with_g4(MINI_CALC_GRAMMAR, "1", "missing_rule")


def test_reuses_generated_parser_for_unchanged_grammar() -> None:
    first = analyze_with_g4(MINI_CALC_GRAMMAR, "1 + 2", "root")
    second = analyze_with_g4(MINI_CALC_GRAMMAR, "3 - 1", "root")

    assert first.accepted and second.accepted
    assert first.generated_directory == second.generated_directory


def _walk(node: ParseTreeNode) -> Iterator[ParseTreeNode]:
    yield node
    for child in node.children:
        yield from _walk(child)
