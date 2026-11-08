"""E2E-01: every ``tests/cps/mips`` fixture through the API, the CLI and the IDE.

The inventory is discovered automatically: a fixture without header, matrix
ID or oracle fails here, and ``--require-mars`` turns a missing simulator into
a failure. Each program is then compiled and executed by the three consumers,
which must agree with each other and with the hand-written oracle.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from pipeline_harness import FIXTURES, fixture_header, fixture_paths, oracle
from src.main import _run_cps_cli, asm_document
from src.mips.pipeline import compile_to_mips
from src.mips_consumer import CancellableMarsRun

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRICES = sorted((REPO_ROOT / 'docs' / 'proyecto3').glob('MATRIZ_BLOQUE*_*.md'))
DEMO_FIXTURES = {  # docs/proyecto3/GUIA_PRUEBAS_Y_PRESENTACION.md, "Demostración propuesta"
    'validos/DEMO-completa', 'validos/REG-presion', 'validos/CALL-recursion',
    'validos/ENV-escape', 'validos/OBJ-herencia-local', 'validos/EXC-captura',
    'invalidos/ERROR-tipos',
}
KINDS = {'validos': 'ACCEPT', 'runtime': 'RUNTIME', 'invalidos': 'REJECT'}


def _matrix_ids() -> set[str]:
    ids = set()
    for matrix in MATRICES:
        ids |= set(re.findall(r'^\| ([A-Z0-9]+-\d{2}) \|', matrix.read_text(encoding='utf-8'),
                              re.MULTILINE))
    return ids


def _program_output(stdout: str) -> str:
    marker = '----- salida del programa (MARS) -----\n'
    return stdout[stdout.index(marker) + len(marker):stdout.index('----- fin de la salida -----')]


def test_e2e_01_fixture_inventory():
    paths = fixture_paths()
    assert len(MATRICES) == 4, 'the four block matrices define the valid IDs'
    known = _matrix_ids()
    relative = {f'{path.parent.name}/{path.stem}' for path in paths}
    assert DEMO_FIXTURES <= relative, 'the presentation programs must exist'
    stems = [path.stem for path in paths]
    assert len(stems) == len(set(stems))
    oracles = {path.stem for path in (FIXTURES / 'esperados').glob('*.json')}
    assert oracles == set(stems)
    covered = set()
    for path in paths:
        ids, expected = fixture_header(path)
        assert ids and set(ids) <= known, f'{path.name}: unknown IDs {set(ids) - known}'
        covered |= set(ids)
        kind, *rest = expected.split()
        assert KINDS[path.parent.name] == kind
        data = oracle(path)
        assert set(data) == {'compile', 'execution'}
        assert set(data['compile']) == {'accepted', 'stage', 'code'}
        if kind == 'REJECT':
            assert data['compile']['accepted'] is False and data['execution'] is None
            assert data['compile']['stage'] == rest[0]
        else:
            assert data['compile']['accepted'] is True
            assert {'exit_code', 'stdout', 'runtime_code'} <= set(data['execution'])
            assert data['execution']['stdout'].endswith('\n')
            expected_code = rest[0] if kind == 'RUNTIME' else None
            assert data['execution']['runtime_code'] == expected_code
    assert {'E2E-01', 'PIPE-01', 'REG-01', 'CALL-04', 'ENV-02', 'OBJ-03', 'EXC-02',
            'STR-01', 'LIST-01'} <= covered


@pytest.fixture(scope='module')
def qt_application():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _ide_compilation(source: str, path: Path) -> object:
    """Run the IDE's own CompilationWorker body and capture its bundle."""
    from src.gui.app import DEFAULT_GRAMMAR, DEFAULT_PROFILE, CompilationWorker

    worker = CompilationWorker(str(DEFAULT_GRAMMAR), str(DEFAULT_PROFILE), source, str(path), 1)
    captured = {}
    worker.completed.connect(lambda bundle: captured.setdefault('bundle', bundle))
    worker.failed.connect(lambda message: captured.setdefault('error', message))
    worker.run()  # synchronous: same code the thread executes
    assert 'error' not in captured, captured.get('error')
    return captured['bundle']['mips_compilation']


@pytest.mark.parametrize('path', fixture_paths(), ids=lambda p: p.stem)
def test_e2e_01_consumers_agree_with_api_and_oracle(path, mars, qt_application, tmp_path,
                                                    monkeypatch, capsys):
    source = path.read_text(encoding='utf-8')
    expected = oracle(path)
    _, header = fixture_header(path)
    api = compile_to_mips(source, path)
    ide = _ide_compilation(source, path)
    assert api.accepted == ide.accepted == expected['compile']['accepted']
    assert api.failed_stage == ide.failed_stage == expected['compile']['stage']

    monkeypatch.setenv('MARS_JAR', str(mars.jar))
    asm = tmp_path / f'{path.stem}.asm'
    exit_code = _run_cps_cli([str(path), '--emit-mips', str(asm), '--run-mips'])
    captured = capsys.readouterr()

    if not api.accepted:
        assert ide.mips is None and api.mips is None
        assert exit_code == 1 and not asm.exists()
        assert 'Ejecutando en MARS' not in captured.out
        return

    assembly = asm_document(api.mips.assembly)
    assert asm_document(ide.mips.assembly) == assembly
    assert asm.read_text(encoding='utf-8') == assembly

    execution = expected['execution']
    assert _program_output(captured.out) == execution['stdout']
    assert exit_code == (0 if execution['runtime_code'] is None else 1)

    ide_run = CancellableMarsRun(ide.mips.assembly, mars).run()
    assert ide_run.stdout == execution['stdout']
    assert ide_run.returncode == execution['exit_code']
    assert ide_run.status == ('success' if header == 'ACCEPT' else 'runtime_error')
