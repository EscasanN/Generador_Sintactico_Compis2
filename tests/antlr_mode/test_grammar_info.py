from pathlib import Path

import pytest

from src.antlr_mode.grammar_info import (
    GrammarInfoError,
    inspect_g4,
    parse_g4_info,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPISCRIPT_GRAMMAR = (
    REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
)


def test_discovers_combined_grammar_and_parser_rules() -> None:
    info = inspect_g4(COMPISCRIPT_GRAMMAR)

    assert info.name == "Compiscript"
    assert info.kind == "combined"
    assert info.default_start_rule == "program"
    assert "functionDeclaration" in info.parser_rules
    assert "classDeclaration" in info.parser_rules
    assert "Literal" not in info.parser_rules


def test_comments_and_literals_do_not_create_false_rules() -> None:
    info = parse_g4_info(
        """
        grammar Demo;
        // fake: ID;
        start
            : 'not:a:rule' item EOF
            ;
        item: ID;
        ID: [a-z]+;
        WS: [ ]+ -> skip;
        """,
        "Demo.g4",
    )

    assert info.parser_rules == ("start", "item")


def test_rejects_text_without_grammar_header() -> None:
    with pytest.raises(GrammarInfoError, match="declaración"):
        parse_g4_info("program: EOF;", "invalid.g4")


def test_requires_filename_to_match_grammar_name(tmp_path: Path) -> None:
    grammar = tmp_path / "WrongName.g4"
    grammar.write_text("grammar ActualName; start: EOF;", encoding="utf-8")

    with pytest.raises(GrammarInfoError, match="ActualName.g4"):
        inspect_g4(grammar)
