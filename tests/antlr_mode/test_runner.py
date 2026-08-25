from pathlib import Path

from src.antlr_mode.runner import analyze_with_g4


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
    assert not result.diagnostics
    assert any(token.token_type == "Identifier" for token in result.tokens)


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
