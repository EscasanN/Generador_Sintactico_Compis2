from pathlib import Path

from src.antlr_mode.grammar_info import inspect_g4
from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.evaluator import SemanticEvaluator
from src.semantic.profile import load_profile, validate_profile
from src.semantic.types import INTEGER


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPISCRIPT_GRAMMAR = (
    REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
)
COMPISCRIPT_SMOKE_PROFILE = (
    Path(__file__).parent / "fixtures" / "compiscript_smoke.semantic.json"
)
MINICALC_GRAMMAR = REPO_ROOT / "tests" / "antlr_mode" / "fixtures" / "MiniCalc.g4"
MINICALC_PROFILE = REPO_ROOT / "semantic_profiles" / "minicalc.semantic.json"
TINY_NUMBER_GRAMMAR = Path(__file__).parent / "fixtures" / "TinyNumber.g4"
TINY_NUMBER_PROFILE = Path(__file__).parent / "fixtures" / "tiny_number.semantic.json"


def test_minicalc_profile_is_compatible_and_uses_registered_actions() -> None:
    grammar = inspect_g4(MINICALC_GRAMMAR)
    profile = load_profile(MINICALC_PROFILE)

    validate_profile(profile, grammar.parser_rules)
    registered = set(SemanticEvaluator().registry.names)

    assert profile.name == "MiniCalc"
    used_actions = {
        action.name
        for binding in profile.bindings
        for action in binding.actions
    }
    assert used_actions <= registered


def test_tiny_number_profile_is_compatible() -> None:
    grammar = inspect_g4(TINY_NUMBER_GRAMMAR)
    profile = load_profile(TINY_NUMBER_PROFILE)

    validate_profile(profile, grammar.parser_rules)
    assert profile.name == "TinyNumber"


def test_compiscript_smoke_profile_is_compatible() -> None:
    grammar = inspect_g4(COMPISCRIPT_GRAMMAR)
    profile = load_profile(COMPISCRIPT_SMOKE_PROFILE)

    validate_profile(profile, grammar.parser_rules)
    assert profile.name == "CompiscriptTraversalSmoke"


def test_minicalc_semantics_accepts_arithmetic_with_native_walker() -> None:
    result = analyze_semantics_with_g4(
        MINICALC_GRAMMAR,
        "10 + 20 - 5",
        MINICALC_PROFILE,
        "root",
        "examples/calculation.mc",
    )

    assert result.accepted
    assert result.syntax_result.native_tree is not None
    assert result.semantic_result is not None
    assert result.semantic_result.value is not None
    assert result.semantic_result.value.type == INTEGER
    assert result.semantic_result.statistics["rules_visited"] >= 4
    assert result.semantic_result.statistics["actions_executed"] == 5


def test_minicalc_reports_semantic_error_with_source_identity() -> None:
    result = analyze_semantics_with_g4(
        MINICALC_GRAMMAR,
        '"text" + 1',
        MINICALC_PROFILE,
        "root",
        "examples/invalid.mc",
    )

    assert result.syntax_result.accepted
    assert not result.accepted
    assert result.semantic_result is not None
    assert result.semantic_result.diagnostics
    assert all(
        diagnostic.location.source_path == "examples/invalid.mc"
        for diagnostic in result.semantic_result.diagnostics
    )
    assert all(
        diagnostic.location.line >= 1 and diagnostic.location.column >= 1
        for diagnostic in result.semantic_result.diagnostics
    )


def test_same_adapter_handles_two_unrelated_grammars_consecutively() -> None:
    minicalc = analyze_semantics_with_g4(
        MINICALC_GRAMMAR,
        "7 - 2",
        MINICALC_PROFILE,
        "root",
    )
    tiny_number = analyze_semantics_with_g4(
        TINY_NUMBER_GRAMMAR,
        "42",
        TINY_NUMBER_PROFILE,
        "start",
    )

    assert minicalc.accepted
    assert tiny_number.accepted
    assert tiny_number.semantic_result is not None
    assert tiny_number.semantic_result.value is not None
    assert tiny_number.semantic_result.value.type == INTEGER
    assert tiny_number.semantic_result.value.constant_value == 42


def test_official_compiscript_grammar_walks_with_generic_listener() -> None:
    result = analyze_semantics_with_g4(
        COMPISCRIPT_GRAMMAR,
        "let value: integer = 7; print(value);",
        COMPISCRIPT_SMOKE_PROFILE,
        "program",
        "examples/official.cps",
    )

    assert result.accepted
    assert result.semantic_result is not None
    assert result.semantic_result.statistics["rules_visited"] > 1
    assert result.semantic_result.statistics["actions_executed"] == 2
