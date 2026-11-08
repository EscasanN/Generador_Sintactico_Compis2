"""IDE consumer of the MIPS backend (IDE-01 to IDE-04), with real MARS and workers.

Qt runs offscreen; human answers to dialogs are mocked, but compilation and
execution use the real ``CompilationWorker``/``ExecutionWorker`` threads and
MARS. Expected outputs are hand-written literals.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtWidgets import QApplication

from src.gui.app import MainWindow
from src.main import asm_document
from src.mips.models import MarsConfig
from src.mips.pipeline import compile_to_mips
from src.mips_consumer import CANCELLED

REPO_ROOT = Path(__file__).resolve().parents[2]
MIPS_FIXTURES = REPO_ROOT / 'tests' / 'cps' / 'mips'
DEMO = MIPS_FIXTURES / 'validos' / 'DEMO-completa.cps'
DEMO_OUTPUT = '30\n120\n11\n12\n75\nAna tiene saldo\n14\n3\ncapturado DIV_ZERO\nfin\n'
LOOP = 'let x: integer = 0;\nwhile (true) {\n  x = x + 1;\n}\n'


@pytest.fixture
def window(mars, monkeypatch):
    monkeypatch.setenv('MARS_JAR', str(mars.jar))
    application = QApplication.instance() or QApplication([])
    main_window = MainWindow()
    yield main_window
    main_window.shutdown_workers()
    main_window.close()
    application.processEvents()


def _settle(window: MainWindow) -> None:
    QApplication.instance().processEvents()


def _compile(window: MainWindow) -> None:
    window._run_compilation()
    assert window._worker.wait(60000)
    _settle(window)
    assert not window._compiling()


def _execute(window: MainWindow) -> None:
    window._run_execution()
    worker = window._execution_worker
    assert worker.wait(60000)
    _settle(window)


def _open(window: MainWindow, path: Path, monkeypatch) -> None:
    monkeypatch.setattr('src.gui.app.QFileDialog.getOpenFileName', lambda *a, **k: (str(path), ''))
    window._open_input()


def _api_assembly(source: str, path=None) -> str:
    return asm_document(compile_to_mips(source, path).mips.assembly)


# -- IDE-01: compile the current buffer -------------------------------------------


def test_ide_01_unsaved_buffer(window, tmp_path, monkeypatch):
    """The unsaved buffer, not the file on disk, produces the ASM and physical layout."""
    disk = tmp_path / 'programa.cps'
    disk.write_text('print(1);\n', encoding='utf-8')
    _open(window, disk, monkeypatch)
    buffer = DEMO.read_text(encoding='utf-8')
    window._editor.setPlainText(buffer)
    disk.write_text('print(2);\n', encoding='utf-8')  # changed on disk meanwhile

    _compile(window)

    assert window._editor.toPlainText() == buffer
    assert window._mips_view.tac_text() == _api_assembly(buffer, str(disk))
    assert window._tabs.currentWidget() is window._mips_view
    tree = window._physical_panel.frame_tree
    labels = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert labels[0].startswith('global  [main]')
    assert any(label.startswith('fn_factorial  [proc_fn_factorial]') for label in labels)
    assert 'registros de activación abstractos del TAC' in window._physical_panel.status_text()
    names = {tree.topLevelItem(0).child(i).text(0)
             for i in range(tree.topLevelItem(0).childCount())}
    assert {'ra', 'fp anterior', 'enlace de acceso', 'valor de retorno'} <= names
    assert window._physical_panel.static_table.rowCount() > 0
    # The abstract TAC view stays available next to the physical one.
    assert window._layout_panel.frame_tree.topLevelItemCount() > 0
    assert 'Estadísticas MIPS' in window._results.toPlainText()


# -- IDE-02: safe export ----------------------------------------------------------


def test_ide_02_export(window, tmp_path, monkeypatch):
    critical = []
    monkeypatch.setattr('src.gui.app.QMessageBox.critical', lambda *a, **k: critical.append(a))
    monkeypatch.setattr('src.gui.app.QMessageBox.information', lambda *a, **k: None)
    window._editor.setPlainText(DEMO.read_text(encoding='utf-8'))
    _compile(window)
    expected = _api_assembly(DEMO.read_text(encoding='utf-8'))

    target = tmp_path / 'demo.asm'
    monkeypatch.setattr('src.gui.app.QFileDialog.getSaveFileName', lambda *a, **k: (str(target), ''))
    window._export_mips()
    assert target.read_bytes() == expected.encode('utf-8')
    assert 'MIPS exportado' in window.statusBar().currentMessage()

    view = window._mips_view
    view.set_search_text('proc_fn_factorial')
    assert view.find_next() and view.selected_text() == 'proc_fn_factorial'
    view.copy_to_clipboard()
    assert QApplication.clipboard().text() == view.tac_text()

    # Cancelling the dialog writes nothing.
    other = tmp_path / 'otro.asm'
    monkeypatch.setattr('src.gui.app.QFileDialog.getSaveFileName', lambda *a, **k: ('', ''))
    window._export_mips()
    assert not other.exists()

    # An I/O failure keeps the previous file intact.
    target.write_text('previo\n', encoding='utf-8')

    def failing_replace(*_args, **_kwargs):
        raise OSError('disco lleno (simulado)')

    monkeypatch.setattr('src.mips_consumer.os.replace', failing_replace)
    monkeypatch.setattr('src.gui.app.QFileDialog.getSaveFileName', lambda *a, **k: (str(target), ''))
    window._export_mips()
    assert target.read_text(encoding='utf-8') == 'previo\n'
    assert critical and list(tmp_path.glob('.demo.asm.*')) == []

    # A rejected compilation never exports the previous assembly.
    monkeypatch.undo()
    monkeypatch.setattr('src.gui.app.QMessageBox.information', lambda *a, **k: None)
    window._editor.setPlainText((MIPS_FIXTURES / 'invalidos' / 'ERROR-tipos.cps').read_text(encoding='utf-8'))
    _compile(window)
    assert not window._export_mips_action.isEnabled()
    monkeypatch.setattr('src.gui.app.QFileDialog.getSaveFileName',
                        lambda *a, **k: pytest.fail('no dialog for a rejected program'))
    window._export_mips()
    assert target.read_text(encoding='utf-8') == 'previo\n'
    assert window._mips_view.tac_text() == ''
    assert 'fase semántica' in window._mips_view.status_text()


# -- IDE-03: execution lifecycle ----------------------------------------------------


def test_ide_03_execution_lifecycle(window, mars, tmp_path, monkeypatch):
    window._editor.setPlainText(DEMO.read_text(encoding='utf-8'))
    _compile(window)
    assert window._execute_btn.isEnabled() and not window._cancel_btn.isEnabled()

    _execute(window)
    panel = window._execution_panel
    assert panel.output_text() == DEMO_OUTPUT
    assert panel.status_text().startswith('Ejecución correcta: success')
    assert window._execute_btn.isEnabled() and window._run_btn.isEnabled()


def test_ide_03_execution_lifecycle_cancel_terminates_java_without_freezing(window, mars, monkeypatch):
    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(mars.jar, timeout=120, step_limit=10 ** 9))
    window._editor.setPlainText(LOOP)
    _compile(window)

    started = time.monotonic()
    window._run_execution()
    assert time.monotonic() - started < 1.0  # the GUI thread is not blocked
    worker = window._execution_worker
    assert worker.isRunning() and window._cancel_btn.isEnabled()
    assert not window._run_btn.isEnabled() and not window._execute_btn.isEnabled()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:  # Qt keeps processing events meanwhile
        QApplication.instance().processEvents()
        time.sleep(0.05)

    window._cancel_execution()
    # Waiting returns only once the Java tree is gone (it holds the output pipes).
    assert worker.wait(15000)
    _settle(window)
    assert 'cancelada por el usuario' in window._execution_panel.status_text()
    assert worker._run._process is None and worker.cancel_requested
    assert window._execute_btn.isEnabled() and not window._cancel_btn.isEnabled()


def test_ide_03_execution_lifecycle_timeout_and_missing_tool(window, mars, tmp_path, monkeypatch):
    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(mars.jar, timeout=2, step_limit=10 ** 9))
    window._editor.setPlainText(LOOP)
    _compile(window)
    _execute(window)
    assert 'timeout' in window._execution_panel.status_text()
    assert 'MIPS-TIMEOUT' in window._execution_panel.tool_text()

    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(tmp_path / 'no-existe.jar'))
    _execute(window)
    assert 'tool_error' in window._execution_panel.status_text()
    assert 'MIPS-TOOL-MISSING' in window._execution_panel.tool_text()
    assert window._execute_btn.isEnabled()

    monkeypatch.undo()
    monkeypatch.setenv('MARS_JAR', str(mars.jar))
    window._editor.setPlainText((MIPS_FIXTURES / 'runtime' / 'EXC-01-division-sin-manejador.cps')
                                .read_text(encoding='utf-8'))
    _compile(window)
    _execute(window)
    assert window._execution_panel.output_text().endswith('RuntimeError: DIV_ZERO\n')
    assert window._execution_panel.status_text().startswith('Ejecución fallida: runtime_error')


def test_ide_03_execution_lifecycle_close_during_execution_stops_java(mars, monkeypatch):
    monkeypatch.setenv('MARS_JAR', str(mars.jar))
    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(mars.jar, timeout=120, step_limit=10 ** 9))
    application = QApplication.instance() or QApplication([])
    main_window = MainWindow()
    main_window._editor.setPlainText(LOOP)
    _compile(main_window)
    main_window._run_execution()
    worker = main_window._execution_worker
    time.sleep(1.5)
    assert worker.isRunning()

    started = time.monotonic()
    assert main_window.close()  # unsaved buffer: the conftest answers Discard
    assert not worker.isRunning() and worker.cancel_requested
    assert time.monotonic() - started < 15
    assert worker._run._process is None
    application.processEvents()


# -- IDE-04: document revisions -----------------------------------------------------


def test_ide_04_stale_results(window, mars, tmp_path, monkeypatch):
    window._editor.setPlainText(DEMO.read_text(encoding='utf-8'))
    _compile(window)
    assert window._export_mips_action.isEnabled()

    # Editing invalidates generate/run/export immediately.
    window._editor.insertPlainText('\n// cambio\n')
    assert window._mips_view.tac_text() == ''
    assert not window._execute_btn.isEnabled()
    assert not window._export_mips_action.isEnabled()
    assert window._physical_panel.frame_tree.topLevelItemCount() == 0

    # A compilation finished for an older revision is discarded.
    window._run_compilation()
    assert window._worker.wait(60000)
    window._editor.insertPlainText('print(99);\n')
    _settle(window)
    assert window._mips_view.tac_text() == ''
    assert 'descartado' in window.statusBar().currentMessage()
    assert not window._execute_btn.isEnabled()

    # An execution of an older revision is cancelled and its output never shown.
    monkeypatch.setattr('src.mips_consumer.default_mars_config',
                        lambda: MarsConfig(mars.jar, timeout=120, step_limit=10 ** 9))
    window._editor.setPlainText(LOOP)
    _compile(window)
    window._run_execution()
    worker = window._execution_worker
    time.sleep(1.0)
    window._editor.insertPlainText('// editado\n')
    assert worker.cancel_requested
    assert worker.wait(15000)
    _settle(window)
    assert window._execution_panel.output_text() == ''
    assert 'cancelada' not in window._execution_panel.status_text()
    assert 'Ejecución descartada' in window.statusBar().currentMessage()
    assert not window._execute_btn.isEnabled()

    # Opening another document also invalidates the current results.
    window._editor.setPlainText(DEMO.read_text(encoding='utf-8'))
    _compile(window)
    other = tmp_path / 'otro.cps'
    other.write_text('print(5);\n', encoding='utf-8')
    _open(window, other, monkeypatch)
    assert window._mips_view.tac_text() == ''
    assert not window._execute_btn.isEnabled()
    _compile(window)
    _execute(window)
    assert window._execution_panel.output_text() == '5\n'


def test_ide_04_stale_results_execution_signal_cannot_revive_old_output(window):
    """A late completed() of a previous revision is ignored even without a worker."""
    from src.mips.models import MipsExecutionResult

    window._editor.setPlainText('print(1);\n')
    _compile(window)
    old_revision = window._document_revision
    window._editor.insertPlainText('print(2);\n')
    window._on_execution_finished(MipsExecutionResult('success', True, '1\n', '', 0), old_revision)
    assert window._execution_panel.output_text() == ''
    assert CANCELLED not in window._execution_panel.status_text()
