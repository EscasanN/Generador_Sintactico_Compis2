"""User-visible regression tests for document safety and theme navigation."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.codegen.pipeline import compile_compiscript
from src.gui.app import MainWindow


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    yield window
    window._editor.document().setModified(False)
    window.close()
    app.processEvents()


def test_clicking_current_document_keeps_unsaved_text_and_undo(window, tmp_path):
    path = tmp_path / "original.cps"
    path.write_text("let x:integer=1;", encoding="utf-8")
    window._load_into_editor(str(path))
    window._editor.moveCursor(QTextCursor.MoveOperation.End)
    window._editor.insertPlainText(" print(x);")
    text = window._editor.toPlainText()

    window._on_file_clicked(window._file_list.item(0))

    assert window._editor.toPlainText() == text
    window._editor.undo()
    assert window._editor.toPlainText() == "let x:integer=1;"


@pytest.mark.parametrize("action", ["open", "new", "close"])
def test_cancel_keeps_the_unsaved_document(window, tmp_path, monkeypatch, action):
    current = tmp_path / "current.cps"
    other = tmp_path / "other.cps"
    current.write_text("let x:integer=1;", encoding="utf-8")
    other.write_text("let y:integer=2;", encoding="utf-8")
    window._load_into_editor(str(current))
    window._editor.insertPlainText("// edit\n")
    text = window._editor.toPlainText()
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(other), ""))
    monkeypatch.setattr("src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: (str(other), ""))

    if action == "open":
        window._open_input()
    elif action == "new":
        window._new_cps()
    else:
        window.show()
        assert not window.close()
    assert window._editor.toPlainText() == text
    assert window._input_path == str(current)
    assert current.read_text(encoding="utf-8") == "let x:integer=1;"
    assert other.read_text(encoding="utf-8") == "let y:integer=2;"


@pytest.mark.parametrize("action", ["open", "new", "close"])
@pytest.mark.parametrize("save", [True, False])
def test_save_or_discard_only_replaces_the_buffer_after_the_users_choice(
    window, tmp_path, monkeypatch, action, save,
):
    current = tmp_path / "current.cps"
    other = tmp_path / "other.cps"
    current.write_text("let x:integer=1;", encoding="utf-8")
    other.write_text("let y:integer=2;", encoding="utf-8")
    window._load_into_editor(str(current))
    window._editor.insertPlainText("// edit\n")
    text = window._editor.toPlainText()
    choice = QMessageBox.StandardButton.Save if save else QMessageBox.StandardButton.Discard
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: choice)
    monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(other), ""))
    monkeypatch.setattr("src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: (str(other), ""))

    if action == "open":
        window._open_input()
        assert window._editor.toPlainText() == "let y:integer=2;"
    elif action == "new":
        window._new_cps()
        assert window._editor.toPlainText() == ""
    else:
        window.show()
        assert window.close()
    assert current.read_text(encoding="utf-8") == (text if save else "let x:integer=1;")


@pytest.mark.parametrize("action", ["open", "new", "close"])
def test_cancelling_save_as_does_not_discard_an_unnamed_buffer(window, tmp_path, monkeypatch, action):
    target = tmp_path / "other.cps"
    target.write_text("let y:integer=2;", encoding="utf-8")
    window._editor.insertPlainText("let unsaved:integer=1;")
    text = window._editor.toPlainText()
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: QMessageBox.StandardButton.Save)
    monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(target), ""))
    paths = iter([(str(target), ""), ("", "")] if action == "new" else [("", "")])
    monkeypatch.setattr("src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: next(paths))

    if action == "open":
        window._open_input()
    elif action == "new":
        window._new_cps()
    else:
        assert not window.close()
    assert window._editor.toPlainText() == text and window._active_file is None
    assert target.read_text(encoding="utf-8") == "let y:integer=2;"


def test_failed_save_keeps_the_document_instead_of_opening_another(window, tmp_path, monkeypatch):
    window._active_file = str(tmp_path / "missing" / "original.cps")
    window._editor.insertPlainText("let unsaved:integer=1;")
    target = tmp_path / "other.cps"
    target.write_text("let y:integer=2;", encoding="utf-8")
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: QMessageBox.StandardButton.Save)
    monkeypatch.setattr("src.gui.app.QMessageBox.critical", lambda *a, **k: None)
    monkeypatch.setattr("src.gui.app.QFileDialog.getOpenFileName", lambda *a, **k: (str(target), ""))

    window._open_input()

    assert window._editor.toPlainText() == "let unsaved:integer=1;"
    assert window._editor.document().isModified()


def test_undoing_to_saved_contents_does_not_prompt_on_close(window, tmp_path, monkeypatch):
    path = tmp_path / "saved.cps"
    path.write_text("let x:integer=1;", encoding="utf-8")
    window._load_into_editor(str(path))
    window._editor.insertPlainText("// edit\n")
    assert window._editor.document().isModified()
    window._editor.undo()
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: pytest.fail("clean buffer prompted"))

    assert not window._editor.document().isModified()
    assert window.close()


def test_saving_same_path_preserves_current_compilation(window, tmp_path):
    path = tmp_path / "saved.cps"
    path.write_text("let x:integer=1;", encoding="utf-8")
    window._load_into_editor(str(path))
    window._editor.insertPlainText("// edit\n")
    window._run_compilation()
    assert window._worker.wait(30000)
    QApplication.instance().processEvents()
    tac = window._tac_view.tac_text()

    assert window._save_file()

    assert not window._editor.document().isModified()
    assert window._tac_view.tac_text() == tac and tac
    assert window._export_action.isEnabled()


@pytest.mark.parametrize("already_named", [True, False])
def test_new_never_truncates_the_file_just_saved_by_its_guard(window, tmp_path, monkeypatch, already_named):
    target = tmp_path / "target.cps"
    if already_named:
        target.write_text("let x:integer=1;", encoding="utf-8")
        window._load_into_editor(str(target))
    window._editor.insertPlainText("// keep this edit\n")
    edited = window._editor.toPlainText()
    monkeypatch.setattr("src.gui.app.QMessageBox.warning", lambda *a, **k: QMessageBox.StandardButton.Save)
    monkeypatch.setattr("src.gui.app.QFileDialog.getSaveFileName", lambda *a, **k: (str(target), ""))

    window._new_cps()

    assert target.read_text(encoding="utf-8") == edited
    assert window._editor.toPlainText() == edited
    assert not window._editor.document().isModified()


def test_theme_keeps_internal_error_heading_visibly_marked_as_error(window):
    window._on_error("failure details")

    window._toggle_theme()

    cursor = window._results.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(1, QTextCursor.MoveMode.KeepAnchor)
    assert cursor.charFormat().foreground().color().name() == window._palette.danger.lower()


@pytest.mark.parametrize("tab", ["_tac_view", "_layout_panel", "_summary", "_tree_tabs"])
def test_changing_theme_preserves_navigation_and_selection(window, tab):
    result = compile_compiscript("function f():integer { return 1; } let x=f();")
    window._on_finished({
        "compilation": result, "result": result.syntax_result,
        "semantic_result": result.semantic_result, "tree_image": None, "tree_error": None,
    })
    window._tabs.setCurrentWidget(getattr(window, tab))
    tree = window._layout_panel.frame_tree
    frame = tree.topLevelItem(1)
    frame.setExpanded(True)
    window._tac_view.set_search_text("fn_f")
    assert window._tac_view.find_next()
    cursor = window._results.textCursor()
    cursor.setPosition(5)
    cursor.setPosition(15, QTextCursor.MoveMode.KeepAnchor)
    window._results.setTextCursor(cursor)
    selected_summary = window._results.textCursor().selectedText()

    window._toggle_theme()

    assert window._tabs.currentWidget() is getattr(window, tab)
    assert tree.topLevelItem(1) is frame and frame.isExpanded()
    assert window._tac_view.selected_text() == "fn_f"
    assert window._results.textCursor().selectedText() == selected_summary
