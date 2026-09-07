"""Black-box-facing tests for the Compiscript command-line workflow."""

from pathlib import Path

from src.main import _run_cps_cli


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cps_cli_uses_bundled_grammar_and_profile_by_default(tmp_path, capsys):
    """Losing either default must prevent a plain ``program.cps`` run."""
    source = tmp_path / "program.cps"
    source.write_text('let message: string = "a" + "b"; let rest = 5 % 2;', encoding="utf-8")

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "semántico" in output.lower()


def test_cps_cli_external_grammar_without_profile_runs_syntax_only(tmp_path, capsys):
    """An unknown grammar must not be paired silently with the Compiscript profile."""
    source = tmp_path / "expression.cps"
    source.write_text("1 + 2", encoding="utf-8")
    grammar = REPO_ROOT / "tests" / "antlr_mode" / "fixtures" / "MiniCalc.g4"

    exit_code = _run_cps_cli(
        [str(source), "--grammar", str(grammar), "--start", "root"]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "solo sintaxis" in output.lower()


def test_cps_cli_returns_rejection_for_semantic_errors(tmp_path, capsys):
    source = tmp_path / "invalid.cps"
    source.write_text('let count: integer = "text";', encoding="utf-8")

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "REJECT" in output
    assert "type" in output
