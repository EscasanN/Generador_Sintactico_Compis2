"""Black-box-facing tests for the Compiscript command-line workflow."""

from src.main import _run_cps_cli


def test_cps_cli_uses_bundled_grammar_and_profile_by_default(tmp_path, capsys):
    """Losing either default must prevent a plain ``program.cps`` run."""
    source = tmp_path / "program.cps"
    source.write_text('let message: string = "a" + "b"; let rest = 5 % 2;', encoding="utf-8")

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "semántico" in output.lower()


def test_cps_cli_can_run_bundled_syntax_only(tmp_path, capsys):
    """La opción de diagnóstico omite semántica sin cambiar de lenguaje."""
    source = tmp_path / "program.cps"
    source.write_text("let value: integer = 2;", encoding="utf-8")

    exit_code = _run_cps_cli([str(source), "--syntax-only"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "sintáctico de compiscript" in output.lower()


def test_cps_cli_returns_rejection_for_semantic_errors(tmp_path, capsys):
    source = tmp_path / "invalid.cps"
    source.write_text('let count: integer = "text";', encoding="utf-8")

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "REJECT" in output
    assert "type" in output
