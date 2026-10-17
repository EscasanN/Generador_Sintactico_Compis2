"""Black-box-facing tests for the Compiscript command-line workflow (OUT-01, OUT-02)."""

from pathlib import Path

import pytest

from src.codegen.pipeline import compile_compiscript
from src.main import _run_cps_cli, tac_document


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO = REPO_ROOT / "tests" / "cps" / "codegen" / "validos" / "DEMO-completa.cps"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_cps_cli_uses_bundled_grammar_and_profile_by_default(tmp_path, capsys):
    """Losing either default must prevent a plain ``program.cps`` run."""
    source = _write(
        tmp_path, "program.cps", 'let message: string = "a" + "b"; let rest = 5 % 2;'
    )

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "semántico" in output.lower()
    assert "Estadísticas TAC" in output


def test_cps_cli_can_run_bundled_syntax_only(tmp_path, capsys):
    """La opción de diagnóstico omite semántica sin cambiar de lenguaje."""
    source = _write(tmp_path, "program.cps", "let value: integer = 2;")

    exit_code = _run_cps_cli([str(source), "--syntax-only"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "ACCEPT" in output
    assert "sintáctico de compiscript" in output.lower()


def test_cps_cli_returns_rejection_for_semantic_errors(tmp_path, capsys):
    source = _write(tmp_path, "invalid.cps", 'let count: integer = "text";')

    exit_code = _run_cps_cli([str(source)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "REJECT" in output
    assert "type" in output
    assert "fase semántica" in output


def test_out_01_emit_tac_prints_exactly_the_pipeline_tac(capsys):
    """OUT-01: stdout holds only the verified TAC that the IDE also shows."""
    expected = compile_compiscript(DEMO.read_text(encoding="utf-8"), DEMO)
    assert expected.accepted

    exit_code = _run_cps_cli([str(DEMO), "--emit-tac"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == tac_document(expected.tac)
    assert captured.out.startswith("global:")
    assert "ACCEPT" in captured.err and "ACCEPT" not in captured.out


def test_out_02_emit_tac_with_path_saves_utf8_file(tmp_path, capsys):
    """OUT-02: an explicit path receives the same TAC in UTF-8."""
    target = tmp_path / "salida" / "demo.tac"

    exit_code = _run_cps_cli([str(DEMO), "--emit-tac", str(target)])

    assert exit_code == 0
    expected = compile_compiscript(DEMO.read_text(encoding="utf-8"), DEMO).tac
    assert target.read_bytes() == tac_document(expected).encode("utf-8")
    output = capsys.readouterr().out
    assert f"TAC guardado en: {target}" in output
    assert "ACCEPT" in output


def test_emit_tac_on_semantic_error_prints_diagnostics_and_no_tac(tmp_path, capsys):
    source = _write(tmp_path, "bad.cps", "let x: integer = y;\n")

    exit_code = _run_cps_cli([str(source), "--emit-tac"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "[ERROR][scope] 1:" in captured.err
    assert "REJECT" in captured.err


def test_emit_tac_with_path_never_writes_a_file_for_a_rejected_program(tmp_path, capsys):
    source = _write(tmp_path, "bad.cps", "let x: integer = ;\n")
    target = tmp_path / "bad.tac"

    exit_code = _run_cps_cli([str(source), "--emit-tac", str(target)])

    assert exit_code == 1
    assert not target.exists()
    output = capsys.readouterr().out
    assert "fase sintáctica" in output and "TAC guardado" not in output


def test_codegen_rejection_reports_the_ir_code_and_location(tmp_path, capsys):
    """OUT-05 (CLI): an IRGEN diagnostic keeps its code and source position."""
    source = _write(
        tmp_path, "static.cps", "class C {\n  let v: integer;\n}\nlet x: integer = C.v;\n"
    )

    exit_code = _run_cps_cli([str(source), "--emit-tac"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "[ERROR][codegen] 4:" in captured.err
    assert "IRGEN-UNSUPPORTED-NODE" in captured.err
    assert "fase de generación de código" in captured.err


def test_show_layout_prints_extended_table_and_activation_records(capsys):
    closure = REPO_ROOT / "tests" / "cps" / "validos" / "FUN-04-closure.cps"

    exit_code = _run_cps_cli([str(closure), "--show-layout"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Tabla de símbolos extendida:" in output
    assert "Almacenamiento" in output and "Offset" in output and "Etiqueta" in output
    assert "fn_exterior.interior" in output
    assert "Registros de activación:" in output
    for slot in ("return_address", "control_link", "access_link", "return_value"):
        assert slot in output
    assert "captura base: dueño fn_exterior" in output


def test_unreadable_source_returns_configuration_exit_code(tmp_path, capsys):
    exit_code = _run_cps_cli([str(tmp_path / "no-existe.cps")])

    assert exit_code == 2
    assert "no se pudo leer" in capsys.readouterr().err


def test_syntax_only_cannot_be_combined_with_tac_options(tmp_path, capsys):
    source = _write(tmp_path, "program.cps", "let value: integer = 2;")

    assert _run_cps_cli([str(source), "--syntax-only", "--emit-tac"]) == 2
    assert _run_cps_cli([str(source), "--syntax-only", "--show-layout"]) == 2


def test_unknown_option_is_a_usage_error(tmp_path, capsys):
    source = _write(tmp_path, "program.cps", "let value: integer = 2;")

    assert _run_cps_cli([str(source), "--no-existe"]) == 2


@pytest.mark.parametrize(
    ("tac", "document"),
    [("", ""), ("global:", "global:\n"), ("global:\n", "global:\n")],
)
def test_tac_document_ends_with_a_single_newline(tac, document):
    assert tac_document(tac) == document
