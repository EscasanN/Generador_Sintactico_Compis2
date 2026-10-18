"""IDE de Compiscript: editar, guardar y compilar programas ``.cps``.

La compilación (sintaxis, semántica, generación de TAC y verificación) se
ejecuta en ``CompilationWorker`` fuera del hilo de Qt mediante la misma API
pública que usa la CLI: ``compile_compiscript``. La ventana solo presenta el
resultado inmutable que entrega el worker; nunca construye ni modifica IR.
"""

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

from src.gui.codegen_results import (
    STAGE_NAMES,
    DiagnosticsTable,
    LayoutPanel,
    TacView,
    collect_diagnostics,
    use_code_font,
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


class CompilationWorker(QThread):
    """Compila el programa completo fuera del hilo de la interfaz (IDE-02)."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        grammar_path: str,
        profile_path: str,
        input_text: str,
        source_path: str | None = None,
        document_revision: int | None = None,
    ) -> None:
        super().__init__()
        self.grammar_path = grammar_path
        self.profile_path = profile_path
        self.input_text = input_text
        self.source_path = source_path
        self.document_revision = document_revision

    def run(self) -> None:
        """Ejecuta ``compile_compiscript`` y prepara la imagen del árbol."""
        try:
            from src.antlr_mode.grammar_info import GrammarInfoError
            from src.antlr_mode.parse_tree_visualizer import render_parse_tree
            from src.antlr_mode.runner import AntlrModeError
            from src.codegen.pipeline import compile_compiscript
            from src.semantic.antlr_adapter import SemanticAdapterError

            try:
                compilation = compile_compiscript(
                    self.input_text,
                    self.source_path,
                    grammar_path=self.grammar_path,
                    profile_path=self.profile_path,
                )
            except (AntlrModeError, GrammarInfoError, SemanticAdapterError) as exc:
                self.failed.emit(str(exc))
                return
            syntax_result = compilation.syntax_result
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
            self.completed.emit(
                {
                    "mode": "compile",
                    "compilation": compilation,
                    "result": syntax_result,
                    "semantic_result": compilation.semantic_result,
                    "tree_image": tree_image,
                    "tree_error": tree_error,
                    "document_revision": self.document_revision,
                }
            )
        except Exception:
            import traceback

            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    """Editor y compilador de programas ``.cps`` de Compiscript."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Compiscript IDE")
        self.setMinimumSize(1180, 760)

        self._g4_path = str(DEFAULT_GRAMMAR)
        self._profile_path = str(DEFAULT_PROFILE)
        self._input_path: str | None = None
        self._active_file: str | None = None
        self._worker: CompilationWorker | None = None
        self._last_bundle: dict | None = None
        self._document_revision = 0
        self._document_snapshot: tuple[str | None, str] = (None, "")
        self._palette: Palette = LIGHT

        self._build_menu()
        self._build_ui()
        self._apply_theme(LIGHT)
        self._editor.textChanged.connect(self._document_changed)
        self.statusBar().showMessage(
            "Listo — escriba, cree o abra un programa .cps y presione Compilar."
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
        self._compile_action = QAction("Compilar", self)
        self._compile_action.setShortcuts(["Ctrl+R", "F5"])
        self._compile_action.triggered.connect(self._run_compilation)
        run_menu.addAction(self._compile_action)
        self._export_action = QAction("Exportar TAC…", self)
        self._export_action.setShortcut("Ctrl+E")
        self._export_action.setEnabled(False)
        self._export_action.triggered.connect(self._export_tac)
        run_menu.addAction(self._export_action)

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

        self._run_btn = QPushButton("Compilar")
        self._run_btn.setToolTip(
            "Sintaxis, semántica y código intermedio (Ctrl+R / F5)"
        )
        self._run_btn.clicked.connect(self._run_compilation)
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
        self._file_list.setMaximumHeight(44)
        self._file_items: dict[str, QListWidgetItem] = {}
        item = QListWidgetItem("Compiscript: ninguno")
        item.setData(Qt.ItemDataRole.UserRole, "input")
        self._file_items["input"] = item
        self._file_list.addItem(item)
        self._file_list.itemClicked.connect(self._on_file_clicked)
        files_layout.addWidget(self._file_list)
        editor_layout.addWidget(files_group)

        self._editor = QTextEdit()
        self._editor.setAcceptRichText(False)
        use_code_font(self._editor)
        self._editor.setPlaceholderText(
            "Escriba o abra aquí un programa Compiscript (.cps)."
        )
        editor_layout.addWidget(self._editor, 1)
        splitter.addWidget(editor_container)

        self._tabs = QTabWidget()
        self._tree_tabs = QTabWidget()
        self._tabs.addTab(self._tree_tabs, "Árbol")

        self._semantic_panel = SemanticResultsPanel()
        self._tabs.addTab(self._semantic_panel, "Semántica")

        self._tac_view = TacView()
        self._tac_view.export_button.clicked.connect(self._export_tac)
        self._tabs.addTab(self._tac_view, "Código TAC")

        self._layout_panel = LayoutPanel()
        self._tabs.addTab(self._layout_panel, "Tabla extendida")

        self._summary = QSplitter(Qt.Orientation.Vertical)
        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._summary.addWidget(self._results)
        self._diagnostics = DiagnosticsTable()
        self._summary.addWidget(self._diagnostics)
        self._summary.setSizes([300, 260])
        self._tabs.addTab(self._summary, "Resumen")
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
        self._document_changed()

    def _open_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir programa Compiscript",
            "",
            "Compiscript (*.cps);;Todos los archivos (*)",
        )
        if not path:
            return
        if self._load_into_editor(path):
            self._set_file_slot("input", "Compiscript", path)

    def _set_file_slot(self, key: str, label: str, path: str) -> None:
        if key != "input":
            raise ValueError(f"slot de archivo no compatible: {key}")
        item = self._file_items[key]
        item.setText(f"{label}: {Path(path).name}")
        item.setToolTip(path)

    def _on_file_clicked(self, item: QListWidgetItem) -> None:
        if item.data(Qt.ItemDataRole.UserRole) == "input" and self._input_path:
            self._load_into_editor(self._input_path)

    def _load_into_editor(self, path: str) -> bool:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return False
        self._input_path = path
        self._editor.setPlainText(text)
        self._active_file = path
        self._document_changed()
        return True

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

        self._document_changed()

    def _document_changed(self) -> None:
        """Invalidate results when the buffer or its document identity changes."""
        snapshot = (self._input_path, self._editor.toPlainText())
        if snapshot == self._document_snapshot:
            return
        self._document_snapshot = snapshot
        self._document_revision += 1
        self._clear_results()
        self._tac_view.set_compilation(None)
        self._layout_panel.set_compilation(None)
        self.statusBar().showMessage("Documento modificado; compile para actualizar los resultados.")

    # ------------------------------------------------------------ compilation

    def _run_compilation(self) -> None:
        """Compila el contenido actual del editor, aunque no esté guardado."""
        if self._worker is not None and self._worker.isRunning():
            return
        source = self._editor.toPlainText()
        self._run_btn.setEnabled(False)
        self._compile_action.setEnabled(False)
        self._clear_results()
        self.statusBar().showMessage("Compilando programa Compiscript…")
        worker = CompilationWorker(
            self._g4_path,
            self._profile_path,
            source,
            self._input_path,
            self._document_revision,
        )
        worker.completed.connect(self._on_finished)
        worker.failed.connect(
            lambda message, revision=self._document_revision: self._on_compilation_error(message, revision)
        )
        self._worker = worker
        worker.start()

    def _clear_results(self) -> None:
        """Ningún resultado anterior queda visible como si fuera actual (IDE-03)."""
        self._last_bundle = None
        self._tree_tabs.clear()
        self._semantic_panel.set_result(None)
        self._tac_view.show_pending()
        self._layout_panel.show_pending()
        self._diagnostics.set_compilation(None)
        self._results.clear()
        self._export_action.setEnabled(False)

    def _finish_run(self) -> None:
        self._run_btn.setEnabled(True)
        self._compile_action.setEnabled(True)

    def _on_finished(self, bundle: dict) -> None:
        self._finish_run()
        revision = bundle.get("document_revision")
        if revision is not None and revision != self._document_revision:
            self.statusBar().showMessage("Resultado descartado: el documento cambió durante la compilación.")
            return
        self._last_bundle = bundle
        self._render_bundle(bundle)
        compilation = bundle["compilation"]
        if compilation.accepted:
            stats = compilation.intermediate_result.statistics
            self.statusBar().showMessage(
                f"Compilación aceptada: {stats['instructions']} instrucciones TAC, "
                f"pico de {stats['temporary_peak']} temporales vivos."
            )
            self._tabs.setCurrentWidget(self._tac_view)
            return
        errors = sum(
            1 for row in collect_diagnostics(compilation) if row.severity == "ERROR"
        )
        stage = STAGE_NAMES.get(compilation.failed_stage, compilation.failed_stage)
        self.statusBar().showMessage(
            f"Compilación rechazada en la fase {stage}: {errors} error(es)."
        )
        self._tabs.setCurrentWidget(self._summary)

    def _on_compilation_error(self, message: str, revision: int) -> None:
        if revision != self._document_revision:
            self._finish_run()
            self.statusBar().showMessage("Resultado descartado: el documento cambió durante la compilación.")
            return
        self._on_error(message)

    def _render_bundle(self, bundle: dict) -> None:
        syntax_result = bundle["result"]
        semantic_result = bundle.get("semantic_result")
        compilation = bundle.get("compilation")

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
        self._tac_view.set_compilation(compilation)
        self._layout_panel.set_compilation(compilation)
        self._diagnostics.set_compilation(compilation)
        self._export_action.setEnabled(
            compilation is not None and compilation.accepted
        )

        lines = [
            "=" * 70,
            "  COMPILACIÓN DE COMPISCRIPT",
            "=" * 70,
            f"Archivo    : {(compilation.source_path if compilation else self._input_path) or '(editor sin guardar)'}",
            f"Gramática  : {syntax_result.grammar.name}",
            f"Regla      : {syntax_result.start_rule}",
            f"Tokens     : {len(syntax_result.tokens)}",
        ]
        if not syntax_result.accepted:
            lines.append("Sintaxis   : ERRORES LÉXICOS O SINTÁCTICOS")
            for diagnostic in syntax_result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.stage} {diagnostic.line}:"
                    f"{diagnostic.column} — {diagnostic.message}"
                )
        else:
            lines.append("Sintaxis   : sin errores léxicos ni sintácticos")
        if semantic_result is None:
            lines.append("Semántica  : no se ejecutó")
        else:
            lines.append(
                f"Semántica  : "
                f"{'ACCEPT' if semantic_result.accepted else 'WITH ERRORS'} "
                f"({len(semantic_result.diagnostics)} diagnóstico(s))"
            )
            for diagnostic in semantic_result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.severity.value} {diagnostic.category.value} "
                    f"{diagnostic.location.line}:{diagnostic.location.column} — "
                    f"{diagnostic.message}"
                )
        lines.extend(self._codegen_summary(compilation))
        if bundle.get("tree_error"):
            lines.append(f"[!] Árbol: {bundle['tree_error']}")

        self._results.setHtml(self._build_results_html(lines))
        self._tabs.setCurrentIndex(self._tabs.indexOf(self._semantic_panel))

    @staticmethod
    def _codegen_summary(compilation: object | None) -> list[str]:
        intermediate = (
            compilation.intermediate_result if compilation is not None else None
        )
        if intermediate is None:
            lines = ["TAC        : no generado"]
        elif intermediate.accepted:
            stats = intermediate.statistics
            lines = [
                "TAC        : ACCEPT (verificado por IRVerifier)",
                f"Estadísticas: {stats['instructions']} instrucciones, "
                f"{stats['procedures']} procedimientos, {stats['labels']} etiquetas, "
                f"{stats['temporaries_created']} temporales creados, pico de "
                f"{stats['temporary_peak']} vivos",
            ]
        else:
            lines = ["TAC        : ERRORES DE GENERACIÓN"]
            for diagnostic in intermediate.diagnostics:
                location = diagnostic.location
                position = (
                    f"{location.line}:{location.column}"
                    if location is not None
                    else "-:-"
                )
                lines.append(
                    f"[!] {diagnostic.code} {position} — {diagnostic.message}"
                )
        if compilation is not None:
            if compilation.accepted:
                lines.append("Resultado  : ACCEPT")
            else:
                stage = STAGE_NAMES.get(
                    compilation.failed_stage, compilation.failed_stage
                )
                lines.append(f"Resultado  : REJECT — fase {stage}; sin TAC")
        return lines

    def _export_tac(self) -> None:
        if not self._tac_view.has_tac():
            QMessageBox.information(
                self, "Sin TAC", "Compile un programa válido antes de exportar."
            )
            return
        suggested = (
            str(Path(self._input_path).with_suffix(".tac")) if self._input_path else ""
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar código intermedio",
            suggested,
            "TAC (*.tac);;Texto (*.txt)",
        )
        if not path:
            return
        try:
            target = self._tac_view.export(path)
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.statusBar().showMessage(f"TAC exportado: {target}")

    def _build_results_html(self, lines: list[str]) -> str:
        parts = [
            '<pre style="font-family:Cascadia Mono,Courier New,monospace;'
            f'font-size:10pt;color:{self._palette.text};">'
        ]
        for line in lines:
            escaped = html.escape(line)
            if (
                "[!]" in line
                or "WITH ERRORS" in line
                or "ERRORES" in line
                or "REJECT" in line
            ):
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
        self._finish_run()
        self._clear_results()
        self._tac_view.set_compilation(None)
        self._layout_panel.set_compilation(None)
        self.statusBar().showMessage("Error interno durante la compilación.")
        escaped = html.escape(message)
        self._results.setHtml(
            '<pre style="font-family:Cascadia Mono,Courier New,monospace;'
            f'font-size:10pt;color:{self._palette.danger};">ERROR:\n{escaped}</pre>'
        )
        self._tabs.setCurrentWidget(self._summary)


def launch_gui() -> None:
    """Inicia la aplicación de escritorio de Compiscript."""
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())


__all__ = ["CompilationWorker", "MainWindow", "launch_gui"]
