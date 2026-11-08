"""CLI consumer of the MIPS backend (CLI-01, CLI-02), always with real MARS.

``--emit-mips``, ``--show-mips-layout`` and ``--run-mips`` are driven through
``_run_cps_cli`` with temporary files and captured stdout/stderr. Expected
program outputs are literals written by hand, never derived from the backend.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.main import _run_cps_cli, asm_document
from src.mips.models import MarsConfig
from src.mips.pipeline import compile_to_mips

REPO_ROOT = Path(__file__).resolve().parents[1]
MIPS_FIXTURES = REPO_ROOT / 'tests' / 'cps' / 'mips'
DEMO = MIPS_FIXTURES / 'validos' / 'DEMO-completa.cps'
DEMO_OUTPUT = '30\n120\n11\n12\n75\nAna tiene saldo\n14\n3\ncapturado DIV_ZERO\nfin\n'
LOOP = 'let x: integer = 0;\nwhile (true) {\n  x = x + 1;\n}\n'


@pytest.fixture
def mars_env(mars, monkeypatch):
    """The CLI finds MARS like a user would: through ``MARS_JAR``."""
    monkeypatch.setenv('MARS_JAR', str(mars.jar))
    return mars


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding='utf-8')
    return path


def _program_output(stdout: str) -> str:
    start = stdout.index('----- salida del programa (MARS) -----\n') + len(
        '----- salida del programa (MARS) -----\n')
    return stdout[start:stdout.index('----- fin de la salida -----')]


# -- CLI-01: options and flows -----------------------------------------------------


def test_cli_01_options_emit_mips_to_stdout_is_only_assembly(capsys):
    exit_code = _run_cps_cli([str(DEMO), '--emit-mips'])

    captured = capsys.readouterr()
    expected = compile_to_mips(DEMO.read_text(encoding='utf-8'), DEMO).mips.assembly
    assert exit_code == 0
    assert captured.out == asm_document(expected)
    assert captured.out.startswith('.data')
    assert 'ACCEPT' in captured.err and 'Estadísticas MIPS' in captured.err


def test_cli_01_options_emit_mips_to_path_writes_utf8_lf(tmp_path, capsys):
    target = tmp_path / 'salida' / 'demo.asm'

    exit_code = _run_cps_cli([str(DEMO), '--emit-mips', str(target)])

    expected = compile_to_mips(DEMO.read_text(encoding='utf-8'), DEMO).mips.assembly
    assert exit_code == 0
    assert target.read_bytes() == asm_document(expected).encode('utf-8')
    assert b'\r\n' not in target.read_bytes()
    assert f'MIPS guardado en: {target}' in capsys.readouterr().out


def test_cli_01_options_run_mips_prints_the_program_output(mars_env, tmp_path, capsys):
    asm, tac = tmp_path / 'p.asm', tmp_path / 'p.tac'

    exit_code = _run_cps_cli([str(DEMO), '--run-mips', '--emit-mips', str(asm),
                              '--emit-tac', str(tac)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert _program_output(out) == DEMO_OUTPUT
    assert 'EJECUCIÓN: success' in out
    assert asm.read_text(encoding='utf-8').startswith('.data')
    assert tac.read_text(encoding='utf-8').startswith('global:')


def test_cli_01_options_show_mips_layout_names_physical_slots(capsys):
    source = MIPS_FIXTURES / 'validos' / 'CALL-recursion.cps'

    exit_code = _run_cps_cli([str(source), '--show-mips-layout', '--show-layout'])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert 'Registros de activación:' in out  # abstract TAC records are kept
    assert 'Frames físicos MIPS32' in out
    assert 'fn_sumarSeis [proc_fn_sumarSeis]' in out
    for name in ('ra', 'fp anterior', 'enlace de acceso', 'valor de retorno'):
        assert f' {name} (' in out
    assert '(área entrante)' in out and 'argumento 5' in out
    assert 'argumentos salientes' in out


@pytest.mark.parametrize('options', [
    ['--syntax-only', '--emit-mips'],
    ['--syntax-only', '--run-mips'],
    ['--syntax-only', '--show-mips-layout'],
    ['--emit-tac', '--emit-mips'],
    ['--run-mips', '--emit-mips'],
    ['--run-mips', '--emit-tac'],
    ['--run-mips', '--emit-tac', '--emit-mips'],
    ['--emit-mips', '--run-mips', '--emit-tac', 'x.tac'],
])
def test_cli_01_options_incompatible_combinations_are_rejected(options, tmp_path, capsys):
    """Any export claiming stdout makes --run-mips invalid, even with all three options."""
    source = _write(tmp_path, 'p.cps', 'print(1);\n')

    assert _run_cps_cli([str(source), *options]) == 2
    captured = capsys.readouterr()
    assert captured.out == '' and captured.err.startswith('ERROR — ')


def test_cli_01_options_run_with_explicit_paths_is_allowed(mars_env, tmp_path, capsys):
    source = _write(tmp_path, 'p.cps', 'print("hola");\n')

    exit_code = _run_cps_cli([str(source), '--emit-tac', str(tmp_path / 'a.tac'),
                              '--emit-mips', str(tmp_path / 'a.asm'), '--run-mips'])

    assert exit_code == 0
    assert _program_output(capsys.readouterr().out) == 'hola\n'


def test_cli_01_options_tac_flow_is_unchanged_without_mips_options(capsys):
    source = REPO_ROOT / 'tests' / 'cps' / 'codegen' / 'validos' / 'DEMO-completa.cps'

    assert _run_cps_cli([str(source), '--emit-tac']) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith('global:') and 'MIPS' not in captured.err


def test_cli_01_options_write_failure_keeps_the_previous_file(tmp_path, monkeypatch, capsys):
    target = _write(tmp_path, 'previo.asm', 'contenido previo\n')

    def failing_replace(*_args, **_kwargs):
        raise OSError('disco lleno (simulado)')

    monkeypatch.setattr('src.mips_consumer.os.replace', failing_replace)
    assert _run_cps_cli([str(DEMO), '--emit-mips', str(target)]) == 2
    assert target.read_text(encoding='utf-8') == 'contenido previo\n'
    assert list(tmp_path.glob('.previo.asm.*')) == []
    assert 'no se pudo guardar el MIPS' in capsys.readouterr().err


# -- CLI-02: exit codes and channels ---------------------------------------------------


@pytest.mark.parametrize(('fixture', 'stage'), [
    ('PIPE-01-error-lexico', 'sintáctica'),
    ('PIPE-01-error-semantico', 'semántica'),
    ('ERROR-tipos', 'semántica'),
    ('PIPE-01-error-tac', 'de generación de código'),
])
def test_cli_02_exit_and_channels_rejection_keeps_existing_files(fixture, stage, tmp_path, capsys):
    source = MIPS_FIXTURES / 'invalidos' / f'{fixture}.cps'
    asm = _write(tmp_path, 'viejo.asm', 'ensamblador anterior\n')

    exit_code = _run_cps_cli([str(source), '--emit-mips', str(asm), '--run-mips'])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert asm.read_text(encoding='utf-8') == 'ensamblador anterior\n'
    assert f'fase {stage}; no se generó TAC ni MIPS' in captured.out
    assert 'El archivo MIPS existente no se actualizó' in captured.err
    assert 'Ejecutando en MARS' not in captured.out


def test_cli_02_exit_and_channels_rejected_stdout_export_prints_nothing(capsys):
    source = MIPS_FIXTURES / 'invalidos' / 'ERROR-tipos.cps'

    assert _run_cps_cli([str(source), '--emit-mips']) == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert '[ERROR][type]' in captured.err and 'REJECT' in captured.err


def test_cli_02_exit_and_channels_program_error_is_exit_one(mars_env, capsys):
    source = MIPS_FIXTURES / 'runtime' / 'EXC-01-division-sin-manejador.cps'

    exit_code = _run_cps_cli([str(source), '--run-mips'])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert _program_output(captured.out).endswith('RuntimeError: DIV_ZERO\n')
    assert 'EJECUCIÓN: runtime_error' in captured.out
    assert 'MIPS-RUNTIME-ERROR' in captured.err


def test_cli_02_exit_and_channels_step_limit_is_not_success(mars_env, tmp_path, capsys):
    source = _write(tmp_path, 'bucle.cps', LOOP)

    assert _run_cps_cli([str(source), '--run-mips']) == 2
    captured = capsys.readouterr()
    assert 'EJECUCIÓN: step_limit' in captured.out
    assert 'MIPS-STEP-LIMIT' in captured.err


def test_cli_02_exit_and_channels_timeout_is_not_success(mars_env, tmp_path, monkeypatch, capsys):
    source = _write(tmp_path, 'bucle.cps', LOOP)
    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(mars_env.jar, timeout=2, step_limit=10 ** 9))

    assert _run_cps_cli([str(source), '--run-mips']) == 2
    captured = capsys.readouterr()
    assert 'EJECUCIÓN: timeout' in captured.out and 'MIPS-TIMEOUT' in captured.err


def test_cli_02_exit_and_channels_missing_mars_is_a_tool_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('MARS_JAR', str(tmp_path / 'no-existe.jar'))
    source = _write(tmp_path, 'p.cps', 'print(1);\n')

    assert _run_cps_cli([str(source), '--run-mips']) == 2
    captured = capsys.readouterr()
    assert 'MIPS-TOOL-MISSING' in captured.err
    assert 'EJECUCIÓN: tool_error' in captured.out


def test_cli_02_exit_and_channels_unreadable_source_is_exit_two(tmp_path, capsys):
    assert _run_cps_cli([str(tmp_path / 'falta.cps'), '--emit-mips']) == 2
    assert 'no se pudo leer' in capsys.readouterr().err
