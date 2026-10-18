"""IDE evidence for Proyecto 2: TAC, extended table, frames and diagnostics.

Covers OUT-03, OUT-04, OUT-05, IDE-01, IDE-02 and IDE-03 from
``docs/proyecto2/MATRIZ_CUMPLIMIENTO.md`` by driving the real ``MainWindow``
with results produced by the same public pipeline as the CLI.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from src.codegen.pipeline import compile_compiscript
from src.gui.app import CompilationWorker, MainWindow
from src.gui.codegen_results import collect_diagnostics, rejection_message
from src.main import tac_document


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "cps" / "codegen"
DEMO = FIXTURES / "validos" / "DEMO-completa.cps"
FAILED_DEMO = FIXTURES / "invalidos" / "DEMO-fallida.cps"
CLOSURES = FIXTURES / "validos" / "FUN-07-closures.cps"


@pytest.fixture
def window():
    application = QApplication.instance() or QApplication([])
    main_window = MainWindow()
    yield main_window
    main_window.close()
    application.processEvents()


def _compile(path: Path):
    return compile_compiscript(path.read_text(encoding="utf-8"), path)


def _bundle(compilation) -> dict:
    """The exact shape ``CompilationWorker`` emits, without Graphviz."""
    return {
        "mode": "compile",
        "compilation": compilation,
        "result": compilation.syntax_result,
        "semantic_result": compilation.semantic_result,
        "tree_image": None,
        "tree_error": None,
    }


def _run_worker_synchronously(window: MainWindow) -> None:
    """Start the real worker thread and deliver its queued signal."""
    application = QApplication.instance()
    window._run_compilation()
    assert window._worker is not None
    assert window._worker.wait(30000)
    application.processEvents()


def _walk(item):
    yield item
    for index in range(item.childCount()):
        yield from _walk(item.child(index))


# -- OUT-03: TAC tab --------------------------------------------------------------


def test_out_03_accepted_program_shows_the_same_tac_as_the_cli(window):
    compilation = _compile(DEMO)

    window._on_finished(_bundle(compilation))

    view = window._tac_view
    assert view.tac_text() == tac_document(compilation.tac)
    assert view.tac_text().startswith("global:")
    assert "TAC verificado" in view.status_text()
    assert window._tabs.currentWidget() is view
    assert window._export_action.isEnabled()
    assert "ACCEPT" in window._results.toPlainText()
    assert "Compilación aceptada" in window.statusBar().currentMessage()


def test_out_03_tac_view_is_monospaced_searchable_copyable_and_exportable(window, tmp_path):
    window._on_finished(_bundle(_compile(DEMO)))
    view = window._tac_view

    assert view._text.isReadOnly()
    assert "monospace" in view._text.styleSheet()
    assert "monospace" in window._editor.styleSheet()
    view.set_search_text("fn_factorial")
    assert view.find_next()
    assert view.selected_text() == "fn_factorial"

    view.copy_to_clipboard()
    assert QApplication.clipboard().text() == view.tac_text()

    target = view.export(tmp_path / "demo.tac")
    assert target.read_bytes() == view.tac_text().encode("utf-8")


def test_out_03_export_menu_writes_the_tac_file(window, tmp_path, monkeypatch):
    window._on_finished(_bundle(_compile(DEMO)))
    target = tmp_path / "exportado.tac"
    monkeypatch.setattr(
        "src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: (str(target), "")
    )

    window._export_tac()

    assert target.read_text(encoding="utf-8") == window._tac_view.tac_text()
    assert "TAC exportado" in window.statusBar().currentMessage()


# -- OUT-04: extended table and activation records ---------------------------------


def test_out_04_extended_table_shows_storage_offset_size_label_and_level(window):
    compilation = _compile(CLOSURES)
    window._on_finished(_bundle(compilation))

    table = window._layout_panel.symbol_table
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    for title in ("Almacenamiento", "Offset", "Tamaño", "Etiqueta", "Nivel"):
        assert title in headers
    rows = compilation.intermediate_result.symbol_layouts.rows()
    assert table.rowCount() == len(rows)
    shown = {
        table.item(r, 0).text(): {
            headers[c]: table.item(r, c).text() for c in range(table.columnCount())
        }
        for r in range(table.rowCount())
    }
    assert shown["contador"]["Etiqueta"] == "fn_contador"
    assert shown["cuenta"]["Almacenamiento"] == "captured"
    assert shown["resultado"]["Offset"] == "0"


def test_out_04_frames_show_header_parameters_locals_temporaries_and_size(window):
    compilation = _compile(CLOSURES)
    window._on_finished(_bundle(compilation))

    tree = window._layout_panel.frame_tree
    frames = compilation.intermediate_result.activation_records
    assert tree.topLevelItemCount() == len(frames)
    first = tree.topLevelItem(0)
    assert first.text(0).startswith("global")

    by_label = {
        tree.topLevelItem(i).text(0).split()[0]: tree.topLevelItem(i)
        for i in range(tree.topLevelItemCount())
    }
    inner = by_label["fn_contador.incrementar.doble"]
    frame = next(f for f in frames if f.label == "fn_contador.incrementar.doble")
    assert inner.text(3) == str(frame.size)
    texts = {item.text(0) for item in _walk(inner)}
    for expected in ("Encabezado", "Parámetros", "Locales", "Temporales", "Capturas",
                     "return_address", "control_link", "access_link", "return_value",
                     "env", "cuenta"):
        assert expected in texts
    capture = next(item for item in _walk(inner) if item.text(1) == "captura")
    assert "distancia 1" in capture.text(4)


# -- OUT-05 and IDE-03: rejected programs -----------------------------------------


def test_out_05_semantic_errors_are_listed_with_phase_type_and_location(window):
    compilation = _compile(FAILED_DEMO)
    window._on_finished(_bundle(compilation))

    table = window._diagnostics
    assert table.rowCount() == 3
    rows = [[table.item(r, c).text() for c in range(table.columnCount())]
            for r in range(table.rowCount())]
    assert {row[0] for row in rows} == {"semántica"}
    assert {row[2] for row in rows} == {"type", "function", "scope"}
    assert all(row[3].isdigit() and row[4].isdigit() for row in rows)
    assert window._tabs.currentWidget() is window._summary
    assert "fase semántica" in window.statusBar().currentMessage()


@pytest.mark.parametrize(
    ("fixture", "phase", "kind"),
    [
        ("PIPE-01-error-lexico.cps", "léxica", "lexer"),
        ("PIPE-01-error-sintactico.cps", "sintáctica", "parser"),
        ("PIPE-04-error-generacion.cps", "generación", "IRGEN-UNSUPPORTED-NODE"),
    ],
)
def test_out_05_every_phase_reports_its_own_diagnostic(fixture, phase, kind):
    rows = collect_diagnostics(_compile(FIXTURES / "invalidos" / fixture))
    matching = [row for row in rows if row.phase == phase and row.kind == kind]
    assert matching and all(row.line is not None for row in matching)


def test_ide_03_compiling_an_invalid_program_clears_the_previous_tac(window):
    window._on_finished(_bundle(_compile(DEMO)))
    assert window._tac_view.has_tac()
    assert window._layout_panel.symbol_table.rowCount() > 0

    rejected = _compile(FAILED_DEMO)
    window._on_finished(_bundle(rejected))

    assert window._tac_view.tac_text() == ""
    assert window._tac_view.status_text() == rejection_message(rejected)
    assert "fase semántica" in window._tac_view.status_text()
    assert window._layout_panel.symbol_table.rowCount() == 0
    assert window._layout_panel.frame_tree.topLevelItemCount() == 0
    assert not window._export_action.isEnabled()
    assert "REJECT" in window._results.toPlainText()


def test_ide_03_starting_a_compilation_clears_results_immediately(window, monkeypatch):
    window._on_finished(_bundle(_compile(DEMO)))
    monkeypatch.setattr(CompilationWorker, "start", lambda worker: None)
    window._editor.setPlainText("let x: integer = 1;")

    window._run_compilation()

    assert window._tac_view.tac_text() == ""
    assert window._tac_view.status_text() == "Compilando…"
    assert window._layout_panel.symbol_table.rowCount() == 0
    assert window._diagnostics.rowCount() == 0
    assert window._tree_tabs.count() == 0
    assert not window._run_btn.isEnabled()
    assert not window._compile_action.isEnabled()


# -- IDE-01 / IDE-02: real end-to-end flow ----------------------------------------


def test_ide_01_and_02_open_edit_compile_valid_then_invalid(window, tmp_path, monkeypatch):
    """Open a .cps, compile it on the worker, then break it and recompile."""
    source = tmp_path / "programa.cps"
    source.write_text(
        "function doble(n: integer): integer { return n * 2; }\n"
        "let x: integer = doble(4);\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(source), "")
    )
    window._open_input()
    assert "doble" in window._editor.toPlainText()

    _run_worker_synchronously(window)
    assert window._run_btn.isEnabled()
    assert "procedure fn_doble" in window._tac_view.tac_text()
    assert window._layout_panel.frame_tree.topLevelItemCount() == 2

    window._editor.setPlainText("let x: integer = doble;\n")
    _run_worker_synchronously(window)
    assert window._tac_view.tac_text() == ""
    assert window._diagnostics.rowCount() >= 1
    assert window._layout_panel.frame_tree.topLevelItemCount() == 0


def test_ide_01_unsaved_editor_buffer_can_be_compiled(window):
    window._editor.setPlainText("let saludo: string = \"hola\";\nprint(saludo);\n")

    _run_worker_synchronously(window)

    assert "call print, 1" in window._tac_view.tac_text()
    assert "(editor sin guardar)" in window._results.toPlainText()


def test_worker_reports_configuration_errors_without_crashing(window):
    window._g4_path = str(REPO_ROOT / "no-existe.g4")
    window._editor.setPlainText("let x: integer = 1;")

    _run_worker_synchronously(window)

    assert window._run_btn.isEnabled()
    assert window._tac_view.tac_text() == ""
    assert "ERROR" in window._results.toPlainText()
    assert "Error interno" in window.statusBar().currentMessage()


def test_theme_change_keeps_the_rendered_compilation(window):
    window._on_finished(_bundle(_compile(DEMO)))
    tac = window._tac_view.tac_text()

    window._toggle_theme()

    assert window._tac_view.tac_text() == tac
    assert window._layout_panel.symbol_table.rowCount() > 0


def test_gui_package_does_not_reimplement_code_generation():
    """IDE rules: the GUI consumes compile_compiscript and never lowers IR."""
    for module in (REPO_ROOT / "src" / "gui").glob("*.py"):
        text = module.read_text(encoding="utf-8")
        for forbidden in ("CompiscriptCodeGenerator", "IRBuilder", "IRVerifier()"):
            assert forbidden not in text, f"{module.name} uses {forbidden}"


@pytest.mark.parametrize("change", ["edit", "open", "save_as"])
def test_document_changes_discard_a_running_workers_obsolete_result(window, tmp_path, monkeypatch, change):
    original = tmp_path / "original.cps"
    changed = tmp_path / "changed.cps"
    original.write_text("let x:integer=1;", encoding="utf-8")
    changed.write_text("let x:integer=;", encoding="utf-8")
    window._input_path = str(original)
    window._load_into_editor(str(original))
    window._run_compilation()
    worker = window._worker
    if change == "edit":
        window._editor.setPlainText("let x:integer=;")
    elif change == "open":
        monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(changed), ""))
        window._open_input()
    else:
        monkeypatch.setattr("src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: (str(changed), ""))
        window._save_file_as()
    assert worker.wait(30000)
    QApplication.instance().processEvents()
    assert window._tac_view.tac_text() == ""
    assert window._last_bundle is None
    assert not window._export_action.isEnabled()
    assert "ACCEPT" not in window._results.toPlainText()
    assert window._run_btn.isEnabled()


def test_editing_after_compilation_immediately_invalidates_export(window):
    window._editor.setPlainText("let x:integer=1;")
    _run_worker_synchronously(window)
    assert window._tac_view.has_tac()
    window._editor.setPlainText("let x:integer=;")
    assert not window._tac_view.has_tac()
    assert not window._export_action.isEnabled()


def test_failed_open_keeps_the_current_document_and_its_result(window, tmp_path, monkeypatch):
    current = tmp_path / "current.cps"
    current.write_text("let x:integer=1;", encoding="utf-8")
    window._input_path = str(current)
    window._load_into_editor(str(current))
    _run_worker_synchronously(window)
    monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(tmp_path / "missing.cps"), ""))
    monkeypatch.setattr("src.gui.app.QMessageBox.critical", lambda *a: None)
    window._open_input()
    assert window._input_path == str(current)
    assert window._tac_view.has_tac()
