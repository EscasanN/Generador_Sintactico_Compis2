"""IDE enfocado exclusivamente en el flujo de Compiscript."""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.parse_tree_view import build_tree_widget
from src.gui.semantic_results import SemanticResultsPanel
from src.gui.theme import DARK, LIGHT, Palette, stylesheet


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAMMAR = (
    REPOSITORY_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
)
DEFAULT_PROFILE = REPOSITORY_ROOT / "semantic_profiles" / "compiscript.semantic.json"
DEFAULT_START_RULE = "program"


class SemanticAnalysisWorker(QThread):
    """Ejecuta sintaxis y semántica fuera del hilo de la interfaz."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        grammar_path: str,
        profile_path: str,
        start_rule: str,
        input_text: str,
        source_path: str | None = None,
    ) -> None:
        super().__init__()
        self.grammar_path = grammar_path
        self.profile_path = profile_path
        self.start_rule = start_rule
        self.input_text = input_text
        self.source_path = source_path

    def run(self) -> None:
        """Compila el texto y prepara las vistas del resultado."""
        try:
            from src.antlr_mode.parse_tree_visualizer import render_parse_tree
            from src.antlr_mode.runner import AntlrModeError
            from src.semantic.antlr_adapter import (
                SemanticAdapterError,
                analyze_semantics_with_g4,
            )

            result = analyze_semantics_with_g4(
                self.grammar_path,
                self.input_text,
                self.profile_path,
                self.start_rule,
                self.source_path,
            )
            syntax_result = result.syntax_result
            tree_image = None
            tree_error = None
            if syntax_result.tree is not None:
                try:
                    output_name = syntax_result.generated_directory.name
                    tree_image = render_parse_tree(
                        syntax_result.tree,
                        f"output/antlr/tree-{output_name}",
                    )
                except Exception as exc:  # pragma: no cover - Graphviz externo
                    tree_error = str(exc)
            self.finished.emit(
                {
                    "mode": "semantic",
                    "result": syntax_result,
                    "semantic_result": result.semantic_result,
                    "tree_image": tree_image,
                    "tree_error": tree_error,
                }
            )
        except (AntlrModeError, SemanticAdapterError) as exc:
            self.error.emit(str(exc))
        except Exception:
            import traceback

            self.error.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    """Editor y analizador de programas ``.cps`` de Compiscript."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Compiscript IDE")
        self.setMinimumSize(1180, 760)

        self._g4_path = str(DEFAULT_GRAMMAR)
        self._profile_path = str(DEFAULT_PROFILE)
        self._input_path: str | None = None
        self._active_file: str | None = None
        self._worker: SemanticAnalysisWorker | None = None
        self._last_bundle: dict | None = None
        self._palette: Palette = LIGHT

        self._build_menu()
        self._build_ui()
        self._apply_theme(LIGHT)
        self.statusBar().showMessage(
            "Listo — cree o abra un programa .cps y presione Analizar."
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Archivo")
        actions = [
            ("Nuevo .cps…", self._new_cps),
            ("Abrir .cps…", self._open_input),
            ("Guardar", self._save_file),
            ("Guardar como…", self._save_file_as),
        ]
        for label, slot in actions:
            action = QAction(label, self)
            action.triggered.connect(slot)
            file_menu.addAction(action)

        run_menu = self.menuBar().addMenu("&Ejecutar")
        analyze_action = QAction("Analizar", self)
        analyze_action.setShortcut("Ctrl+R")
        analyze_action.triggered.connect(self._run_analysis)
        run_menu.addAction(analyze_action)

        view_menu = self.menuBar().addMenu("&Vista")
        theme_action = QAction("Cambiar tema", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        for label, slot in [
            ("Nuevo", self._new_cps),
            ("Abrir .cps", self._open_input),
            ("Guardar", self._save_file),
        ]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            toolbar.addWidget(button)

        self._run_btn = QPushButton("Analizar")
        self._run_btn.clicked.connect(self._run_analysis)
        toolbar.addWidget(self._run_btn)
        toolbar.addStretch()

        configuration = QLabel(
            f"Gramática: {DEFAULT_GRAMMAR.name}  |  "
            f"Perfil: {DEFAULT_PROFILE.name}  |  Regla: {DEFAULT_START_RULE}"
        )
        configuration.setObjectName("sectionTitle")
        toolbar.addWidget(configuration)

        self._theme_btn = QPushButton("Modo oscuro")
        self._theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(self._theme_btn)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        files_group = QGroupBox("Programa")
        files_layout = QVBoxLayout(files_group)
        self._file_list = QListWidget()
        self._file_items: dict[str, QListWidgetItem] = {}
        item = QListWidgetItem("Compiscript: ninguno")
        item.setData(Qt.ItemDataRole.UserRole, "input")
        self._file_items["input"] = item
        self._file_list.addItem(item)
        self._file_list.itemClicked.connect(self._on_file_clicked)
        files_layout.addWidget(self._file_list)
        editor_layout.addWidget(files_group)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText(
            "Escriba o abra aquí un programa Compiscript (.cps)."
        )
        editor_layout.addWidget(self._editor, 1)
        splitter.addWidget(editor_container)

        self._tabs = QTabWidget()
        self._tree_tabs = QTabWidget()
        self._tabs.addTab(self._tree_tabs, "Árbol sintáctico")

        self._semantic_panel = SemanticResultsPanel()
        self._tabs.addTab(self._semantic_panel, "Semántica")

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._tabs.addTab(self._results, "Resultados")
        splitter.addWidget(self._tabs)
        splitter.setSizes([520, 660])
        root.addWidget(splitter, 1)

    def _apply_theme(self, palette: Palette) -> None:
        self._palette = palette
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(palette))
        self._theme_btn.setText(
            "Modo claro" if palette.name == "dark" else "Modo oscuro"
        )
        if self._last_bundle is not None:
            self._render_bundle(self._last_bundle)

    def _toggle_theme(self) -> None:
        self._apply_theme(DARK if self._palette.name == "light" else LIGHT)

    def _ensure_cps_suffix(self, path: str) -> str:
        return path if Path(path).suffix.lower() == ".cps" else f"{path}.cps"

    def _new_cps(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Nuevo programa Compiscript",
            "",
            "Compiscript (*.cps)",
        )
        if not path:
            return
        path = self._ensure_cps_suffix(path)
        try:
            Path(path).write_text("", encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._input_path = path
        self._active_file = path
        self._set_file_slot("input", "Compiscript", path)
        self._editor.clear()

    def _open_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir programa Compiscript",
            "",
            "Compiscript (*.cps);;Todos los archivos (*)",
        )
        if not path:
            return
        self._input_path = path
        self._set_file_slot("input", "Compiscript", path)
        self._load_into_editor(path)

    def _set_file_slot(self, key: str, label: str, path: str) -> None:
        if key != "input":
            raise ValueError(f"slot de archivo no compatible: {key}")
        item = self._file_items[key]
        item.setText(f"{label}: {Path(path).name}")
        item.setToolTip(path)

    def _on_file_clicked(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.UserRole) == "input" and self._input_path:
            self._load_into_editor(self._input_path)

    def _load_into_editor(self, path: str) -> None:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._editor.setPlainText(text)
        self._active_file = path

    def _save_file(self) -> None:
        if self._active_file is None:
            self._save_file_as()
            return
        try:
            Path(self._active_file).write_text(
                self._editor.toPlainText(), encoding="utf-8"
            )
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.statusBar().showMessage(f"Guardado: {self._active_file}")

    def _save_file_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar programa Compiscript",
            self._active_file or "",
            "Compiscript (*.cps)",
        )
        if not path:
            return
        path = self._ensure_cps_suffix(path)
        try:
            Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._input_path = path
        self._active_file = path
        self._set_file_slot("input", "Compiscript", path)

    def _run_analysis(self) -> None:
        self._run_semantic_analysis()

    def _run_semantic_analysis(self) -> None:
        if self._input_path is None:
            QMessageBox.warning(
                self,
                "Falta programa",
                "Primero cree o abra un archivo .cps.",
            )
            return
        source = self._editor.toPlainText()
        self._run_btn.setEnabled(False)
        self.statusBar().showMessage("Analizando programa Compiscript…")
        self._worker = SemanticAnalysisWorker(
            self._g4_path,
            self._profile_path,
            DEFAULT_START_RULE,
            source,
            self._input_path,
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, bundle: dict) -> None:
        self._run_btn.setEnabled(True)
        self._last_bundle = bundle
        self._render_bundle(bundle)
        semantic_result = bundle.get("semantic_result")
        accepted = semantic_result is not None and semantic_result.accepted
        self.statusBar().showMessage(
            "Análisis completado: ACCEPT"
            if accepted
            else "Análisis completado con errores"
        )

    def _render_bundle(self, bundle: dict) -> None:
        self._render_semantic_bundle(bundle)

    def _render_semantic_bundle(self, bundle: dict) -> None:
        syntax_result = bundle["result"]
        semantic_result = bundle.get("semantic_result")

        self._tree_tabs.clear()
        image_path = bundle.get("tree_image")
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                image_label.setText("No se pudo cargar la imagen del árbol.")
            else:
                image_label.setPixmap(pixmap)
                image_label.adjustSize()
        elif bundle.get("tree_error"):
            image_label.setText(f"Error al renderizar: {bundle['tree_error']}")
        else:
            image_label.setText("No se produjo una imagen del árbol.")
        image_scroll.setWidget(image_label)
        self._tree_tabs.addTab(image_scroll, "Imagen")

        if syntax_result.tree is not None:
            self._tree_tabs.addTab(
                build_tree_widget(syntax_result.tree),
                "Navegable",
            )

        self._semantic_panel.set_result(semantic_result)
        lines = [
            "=" * 70,
            "  ANÁLISIS DE COMPISCRIPT",
            "=" * 70,
            f"Archivo    : {self._input_path or '(memoria)'}",
            f"Gramática  : {syntax_result.grammar.name}",
            f"Regla      : {syntax_result.start_rule}",
            f"Tokens     : {len(syntax_result.tokens)}",
        ]
        if not syntax_result.accepted:
            lines.append("Resultado  : ERRORES SINTÁCTICOS")
            for diagnostic in syntax_result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.stage} {diagnostic.line}:"
                    f"{diagnostic.column} — {diagnostic.message}"
                )
        elif semantic_result is None:
            lines.append("Resultado  : la semántica no se ejecutó")
        else:
            lines.append(
                f"Resultado  : {'ACCEPT' if semantic_result.accepted else 'WITH ERRORS'}"
            )
            lines.append(f"Diagnósticos: {len(semantic_result.diagnostics)}")
            for diagnostic in semantic_result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.severity.value} {diagnostic.category.value} "
                    f"{diagnostic.location.line}:{diagnostic.location.column} — "
                    f"{diagnostic.message}"
                )
        if bundle.get("tree_error"):
            lines.append(f"[!] Árbol: {bundle['tree_error']}")

        self._results.setHtml(self._build_results_html(lines))
        self._tabs.setCurrentIndex(self._tabs.indexOf(self._semantic_panel))

    def _build_results_html(self, lines: list[str]) -> str:
        parts = [
            '<pre style="font-family:Cascadia Mono,Courier New,monospace;'
            f'font-size:10pt;color:{self._palette.text};">'
        ]
        for line in lines:
            escaped = html.escape(line)
            if "[!]" in line or "WITH ERRORS" in line or "ERRORES" in line:
                parts.append(
                    f'<span style="color:{self._palette.danger};">{escaped}</span>'
                )
            elif "ACCEPT" in line:
                parts.append(
                    f'<span style="color:{self._palette.success};">{escaped}</span>'
                )
            else:
                parts.append(escaped)
            parts.append("\n")
        parts.append("</pre>")
        return "".join(parts)

    def _on_error(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self.statusBar().showMessage("Error durante el análisis.")
        escaped = html.escape(message)
        self._results.setHtml(
            '<pre style="font-family:Cascadia Mono,Courier New,monospace;'
            f'font-size:10pt;color:{self._palette.danger};">ERROR:\n{escaped}</pre>'
        )
        self._tabs.setCurrentIndex(self._tabs.indexOf(self._results))


def launch_gui() -> None:
    """Inicia la aplicación de escritorio de Compiscript."""
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())


__all__ = ["MainWindow", "SemanticAnalysisWorker", "launch_gui"]
