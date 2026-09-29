import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.antlr_mode.parse_tree_visualizer import render_parse_tree
from src.gui.app import MainWindow
from src.semantic.antlr_adapter import analyze_semantics_with_g4


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"


def test_main_window_is_configured_only_for_compiscript() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        assert window.windowTitle() == "Compiscript IDE"
        assert window._file_list.count() == 1
        assert Path(window._g4_path) == GRAMMAR
        assert Path(window._profile_path) == PROFILE

        result = analyze_semantics_with_g4(
            GRAMMAR,
            "let value: integer = 7;",
            PROFILE,
            "program",
            "programa.cps",
        )
        tree_image = render_parse_tree(
            result.syntax_result.tree,
            "output/antlr/test-gui-tree",
        )
        window._render_bundle(
            {
                "mode": "semantic",
                "result": result.syntax_result,
                "semantic_result": result.semantic_result,
                "tree_image": tree_image,
                "tree_error": None,
            }
        )

        assert window._tree_tabs.count() == 2
        assert "ACCEPT" in window._results.toPlainText()
    finally:
        window.close()
        application.processEvents()
