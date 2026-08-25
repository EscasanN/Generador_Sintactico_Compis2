import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.antlr_mode.runner import analyze_with_g4
from src.gui.app import MainWindow
from src.utils.visualizer import render_parse_tree


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPISCRIPT_GRAMMAR = (
    REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
)


def test_main_window_exposes_both_modes_and_g4_rules() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert window._mode_combo.count() == 2
        assert window._file_list.count() == 4

        window._load_g4_rules(str(COMPISCRIPT_GRAMMAR))
        window._set_mode("antlr")

        assert window._mode_combo.currentData() == "antlr"
        assert window._start_rule_combo.isEnabled()
        assert window._start_rule_combo.currentText() == "program"
        assert window._start_rule_combo.findText("classDeclaration") >= 0

        window._set_mode("yapar")
        assert window._mode_combo.currentData() == "yapar"
        assert not window._start_rule_combo.isEnabled()

        result = analyze_with_g4(
            COMPISCRIPT_GRAMMAR,
            "let value: integer = 7;",
            "program",
        )
        tree_image = render_parse_tree(
            result.tree,
            "output/antlr/test-gui-tree",
        )
        window._render_antlr_bundle({
            "mode": "antlr",
            "result": result,
            "tree_image": tree_image,
            "tree_error": None,
        })

        assert window._table_tabs.count() == 1
        assert window._tree_tabs.count() == 1
        assert "ACCEPT" in window._results.toPlainText()
    finally:
        window.close()
        application.processEvents()
