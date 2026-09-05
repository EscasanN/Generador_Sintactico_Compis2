"""GUI coverage for the .cps IDE workflow (block 4, Nelson).

Every ``IDE-xx`` identifier from ``docs/phase3/MATRIZ_CUMPLIMIENTO.md`` gets
at least one assertion here, driving the real ``MainWindow`` the same way
``tests/antlr_mode/test_gui_mode.py`` already does for the generic ANTLR
mode -- this file focuses specifically on the Compiscript ``.cps`` workflow
(new/open/edit/save, compiling with a semantic profile, diagnostics, the
per-environment symbol table, the navigable tree, and running off the Qt
thread). It never touches ``tests/antlr_mode/test_gui_mode.py`` or the
behaviour it already locks in.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.antlr_mode.runner import analyze_with_g4
from src.gui.app import MainWindow, SemanticAnalysisWorker
from src.gui.semantic_bridge import analyze_semantics_with_extensions
from src.utils.visualizer import render_parse_tree


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"

VALID_PROGRAM = "let value: integer = 7; print(value);"
INVALID_PROGRAM = "let value: integer = 7; let value: integer = 8;"


def _make_window() -> tuple[QApplication, MainWindow]:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    return application, window


def test_ide_01_and_02_open_and_edit_a_cps_file(tmp_path):
    """IDE-01 / IDE-02: opening a .cps shows its content, editing is allowed."""
    application, window = _make_window()
    try:
        cps_path = tmp_path / "programa.cps"
        cps_path.write_text(VALID_PROGRAM, encoding="utf-8")

        window._input_path = str(cps_path)
        window._set_file_slot("input", "Input", str(cps_path))
        window._load_into_editor(str(cps_path))

        assert window._editor.toPlainText() == VALID_PROGRAM
        assert not window._editor.isReadOnly()

        window._editor.setPlainText(VALID_PROGRAM + "\nprint(1);")
        assert "print(1);" in window._editor.toPlainText()
    finally:
        window.close()
        application.processEvents()


def test_ide_01_file_list_slot_still_accepts_cps(tmp_path):
    """Loaded-files list keeps exactly its four slots (regression) and one is Input."""
    application, window = _make_window()
    try:
        assert window._file_list.count() == 4
        cps_path = tmp_path / "programa.cps"
        cps_path.write_text(VALID_PROGRAM, encoding="utf-8")
        window._input_path = str(cps_path)
        window._set_file_slot("input", "Input", str(cps_path))
        assert window._file_items["input"].text() == f"Input: {cps_path.name}"
    finally:
        window.close()
        application.processEvents()


def test_ide_03_new_and_save_as_keep_the_cps_extension(tmp_path, monkeypatch):
    """IDE-03: New .cps and Save As never silently drop the .cps extension."""
    application, window = _make_window()
    try:
        new_path = tmp_path / "nuevo.cps"
        monkeypatch.setattr(
            "src.gui.app.QFileDialog.getSaveFileName",
            lambda *a, **k: (str(new_path), ""),
        )
        window._new_cps()
        assert window._active_file == str(new_path)
        assert Path(new_path).exists()
        assert window._editor.toPlainText() == ""

        window._editor.setPlainText(VALID_PROGRAM)
        saved_as_path = tmp_path / "guardado.cps"
        monkeypatch.setattr(
            "src.gui.app.QFileDialog.getSaveFileName",
            lambda *a, **k: (str(saved_as_path), ""),
        )
        window._save_file_as()
        assert saved_as_path.read_text(encoding="utf-8") == VALID_PROGRAM
        assert str(saved_as_path).endswith(".cps")
    finally:
        window.close()
        application.processEvents()


def test_ide_04_and_05_compile_reports_categorized_diagnostics_with_location():
    """IDE-04 / IDE-05: compiling runs syntax+semantics and reports location."""
    application, window = _make_window()
    try:
        result = analyze_semantics_with_extensions(
            GRAMMAR, INVALID_PROGRAM, PROFILE, "program", "programa.cps"
        )
        assert result.syntax_result.accepted
        assert not result.accepted

        tree_image = render_parse_tree(
            result.syntax_result.tree, "output/antlr/test-gui-semantic-tree"
        )
        window._profile_path = str(PROFILE)
        window._render_bundle({
            "mode": "semantic",
            "result": result.syntax_result,
            "semantic_result": result.semantic_result,
            "tree_image": tree_image,
            "tree_error": None,
        })

        table = window._semantic_panel._diagnostics_table
        assert table.rowCount() >= 1
        row_texts = [table.item(0, col).text() for col in range(5)]
        severity, category, line, column, message = row_texts
        assert severity == "ERROR"
        assert category  # a real category name, e.g. "scope"
        assert line.isdigit() and int(line) >= 1
        assert column.isdigit() and int(column) >= 1
        assert message
        assert "ACCEPT" not in window._results.toPlainText()
    finally:
        window.close()
        application.processEvents()


def test_ide_06_symbol_table_shows_every_environment_kind():
    """IDE-06: global, function, class and block scopes are all consultable."""
    application, window = _make_window()
    try:
        source = """
        let g: integer = 1;
        function f(): integer {
          let local: integer = 1;
          return local;
        }
        class C {
          let field: integer;
          function constructor() { this.field = 1; }
        }
        { let blockVar: integer = 1; }
        """
        result = analyze_semantics_with_extensions(
            GRAMMAR, source, PROFILE, "program", "programa.cps"
        )
        assert result.accepted
        window._semantic_panel.set_result(result.semantic_result)

        tree = window._semantic_panel._symbol_tree
        collected_kinds = set()

        def walk(item):
            collected_kinds.add(item.text(0).split(":")[0])
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i))

        assert "global" in collected_kinds
        assert "function" in collected_kinds
        assert "class" in collected_kinds
        assert "block" in collected_kinds
    finally:
        window.close()
        application.processEvents()


def test_ide_07_parse_tree_has_both_image_and_navigable_views():
    """IDE-07: the tree is available as an image and as a navigable widget."""
    application, window = _make_window()
    try:
        result = analyze_with_g4(GRAMMAR, VALID_PROGRAM, "program")
        tree_image = render_parse_tree(result.tree, "output/antlr/test-gui-navigable")
        window._profile_path = None
        window._render_bundle({
            "mode": "semantic",
            "result": result,
            "semantic_result": None,
            "tree_image": tree_image,
            "tree_error": None,
        })
        # One tab for the Graphviz image, one for the navigable QTreeWidget.
        assert window._tree_tabs.count() == 2
        assert window._tree_tabs.tabText(1) == "Navigable"
    finally:
        window.close()
        application.processEvents()


def test_ide_08_semantic_analysis_runs_on_a_worker_thread():
    """IDE-08: compiling never blocks the GUI thread."""
    application = QApplication.instance() or QApplication([])
    worker = SemanticAnalysisWorker(
        str(GRAMMAR), str(PROFILE), "program", VALID_PROGRAM, "programa.cps"
    )
    from PyQt6.QtCore import QThread

    assert isinstance(worker, QThread)

    captured = {}
    worker.finished.connect(lambda bundle: captured.setdefault("bundle", bundle))
    worker.error.connect(lambda message: captured.setdefault("error", message))
    worker.start()
    worker.wait(15000)
    application.processEvents()

    assert "error" not in captured
    assert captured["bundle"]["mode"] == "semantic"
    assert captured["bundle"]["semantic_result"] is not None
    assert captured["bundle"]["semantic_result"].accepted


def test_regression_yapar_mode_round_trip_is_unaffected():
    """The pre-existing YAPar mode keeps working after the .cps additions."""
    application, window = _make_window()
    try:
        assert window._mode_combo.count() == 2
        window._set_mode("yapar")
        assert window._mode_combo.currentData() == "yapar"
        assert not window._start_rule_combo.isEnabled()
    finally:
        window.close()
        application.processEvents()


def test_regression_antlr_and_compiscript_modes_run_consecutively():
    """MiniCalc-style ANTLR runs and a Compiscript compile can share one window."""
    application, window = _make_window()
    try:
        window._load_g4_rules(str(GRAMMAR))
        window._set_mode("antlr")

        syntax_only = analyze_with_g4(GRAMMAR, VALID_PROGRAM, "program")
        window._render_bundle({
            "mode": "antlr",
            "result": syntax_only,
            "tree_image": None,
            "tree_error": None,
        })
        assert window._tree_tabs.count() == 1

        full = analyze_semantics_with_extensions(
            GRAMMAR, VALID_PROGRAM, PROFILE, "program", "programa.cps"
        )
        window._profile_path = str(PROFILE)
        window._render_bundle({
            "mode": "semantic",
            "result": full.syntax_result,
            "semantic_result": full.semantic_result,
            "tree_image": None,
            "tree_error": None,
        })
        assert window._tree_tabs.count() == 2
        assert window._semantic_panel._diagnostics_table.rowCount() == 0
    finally:
        window.close()
        application.processEvents()
