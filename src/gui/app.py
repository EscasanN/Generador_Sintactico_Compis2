"""IDE de Compiscript: editar, guardar, compilar a TAC/MIPS y ejecutar en MARS.

La compilación (sintaxis, semántica, TAC verificado y ensamblador MIPS) se
ejecuta en ``CompilationWorker`` y la ejecución explícita en MARS en
``ExecutionWorker``, ambos fuera del hilo de Qt y con las mismas APIs públicas
que usa la CLI (``compile_compiscript``/``generate_mips`` y la ejecución de
``src.mips_consumer``). Cada resultado viaja con la revisión del documento que
lo originó; uno de una revisión anterior se descarta. La ventana solo presenta
resultados inmutables: nunca construye ni modifica IR o ensamblador.
"""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QImageReader, QPixmap
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
from src.gui.mips_results import (
    STAGE_NAMES_MIPS,
    ExecutionPanel,
    MipsView,
    PhysicalLayoutPanel,
    mips_diagnostic_lines,
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


def load_tree_pixmap(path: str) -> QPixmap:
    """Graphviz tree image at full resolution.

    Qt refuses to decode images above 256 MB by default; the tree of a large
    program (``DEMO-completa``: 18539 x 3672 px) exceeds it. The file is our own
    Graphviz output, so the limit is raised just enough for it.
    """
    reader = QImageReader(path)
    size = reader.size()
    needed = -(-size.width() * size.height() * 4 // 2**20)  # MB of RGBA, rounded up
    if needed > QImageReader.allocationLimit():
        QImageReader.setAllocationLimit(needed)
    return QPixmap.fromImage(reader.read())


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

            from src.mips.generator import generate_mips
            from src.mips.models import MipsCompilationResult

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
            # Same composition as ``compile_to_mips``: the backend only runs on
            # an accepted TAC, and the grammar/profile chosen by the window apply.
            mips_compilation = MipsCompilationResult(
                compilation,
                generate_mips(compilation.intermediate_result) if compilation.accepted else None,
            )
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
                    "mips_compilation": mips_compilation,
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


class ExecutionWorker(QThread):
    """Ejecuta en MARS fuera del hilo de Qt; ``request_cancel`` termina Java (IDE-03)."""

    completed = pyqtSignal(object, int)

    def __init__(self, assembly: str, config: object, document_revision: int) -> None:
        super().__init__()
        from src.mips_consumer import CancellableMarsRun

        self.document_revision = document_revision
        self._run = CancellableMarsRun(assembly, config)

    @property
    def cancel_requested(self) -> bool:
        return self._run.cancelled

    def request_cancel(self) -> None:
        self._run.cancel()

    def run(self) -> None:
        try:
            result = self._run.run()
        except Exception as exc:  # pragma: no cover - defensa ante fallos inesperados
            from src.mips.diagnostics import MipsDiagnostic
            from src.mips.models import MipsExecutionResult

            result = MipsExecutionResult('tool_error', diagnostics=(
                MipsDiagnostic('MIPS-TOOL-MISSING', repr(exc), phase='tool'),))
        self.completed.emit(result, self.document_revision)


class MainWindow(QMainWindow):
    """Editor y compilador de programas ``.cps`` de Compiscript."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Compiscript IDE[*]")
        self.setMinimumSize(1180, 760)

        self._g4_path = str(DEFAULT_GRAMMAR)
        self._profile_path = str(DEFAULT_PROFILE)
        self._input_path: str | None = None
        self._active_file: str | None = None
        self._worker: CompilationWorker | None = None
        self._execution_worker: ExecutionWorker | None = None
        self._compile_pending = False
        self._mips_compilation: object | None = None
        self._last_bundle: dict | None = None
        self._document_revision = 0
        self._document_snapshot: tuple[str | None, str] = (None, "")
        self._saved_text = ""
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
        run_menu.addSeparator()
        self._run_mips_action = QAction("Ejecutar en MARS", self)
        self._run_mips_action.setShortcuts(["Ctrl+Shift+R", "F6"])
        self._run_mips_action.triggered.connect(self._run_execution)
        run_menu.addAction(self._run_mips_action)
        self._cancel_action = QAction("Cancelar ejecución", self)
        self._cancel_action.setShortcut("Ctrl+.")
        self._cancel_action.triggered.connect(self._cancel_execution)
        run_menu.addAction(self._cancel_action)
        self._export_mips_action = QAction("Exportar MIPS…", self)
        self._export_mips_action.setShortcut("Ctrl+Shift+E")
        self._export_mips_action.triggered.connect(self._export_mips)
        run_menu.addAction(self._export_mips_action)

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
        self._execute_btn = QPushButton("Ejecutar en MARS")
        self._execute_btn.setToolTip("Ejecuta el MIPS de la compilación vigente (F6)")
        self._execute_btn.clicked.connect(self._run_execution)
        toolbar.addWidget(self._execute_btn)
        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setToolTip("Termina la ejecución de MARS en curso")
        self._cancel_btn.clicked.connect(self._cancel_execution)
        toolbar.addWidget(self._cancel_btn)
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

        self._mips_view = MipsView()
        self._mips_view.export_button.clicked.connect(self._export_mips)
        self._tabs.addTab(self._mips_view, "MIPS")

        self._physical_panel = PhysicalLayoutPanel()
        self._tabs.addTab(self._physical_panel, "Frames MIPS")

        self._execution_panel = ExecutionPanel()
        self._execution_panel.run_button.clicked.connect(self._run_execution)
        self._execution_panel.cancel_button.clicked.connect(self._cancel_execution)
        self._tabs.addTab(self._execution_panel, "Ejecución MARS")

        self._summary = QSplitter(Qt.Orientation.Vertical)
        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._summary.addWidget(self._results)
        self._diagnostics = DiagnosticsTable()
        self._summary.addWidget(self._diagnostics)
        self._summary.setSizes([300, 260])
        self._tabs.addTab(self._summary, "Resumen")
        splitter.addWidget(self._tabs)
        splitter.setSizes([480, 700])
        root.addWidget(splitter, 1)
        self._refresh_actions()

    def _apply_theme(self, palette: Palette) -> None:
        self._palette = palette
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(palette))
        self._theme_btn.setText(
            "Modo claro" if palette.name == "dark" else "Modo oscuro"
        )
        if self._results.toPlainText():
            # Only recolor the summary's inline HTML. Rebuilding the bundle
            # would reset tabs, searches, tree expansion and selections.
            cursor = self._results.textCursor()
            anchor, position = cursor.anchor(), cursor.position()
            vertical = self._results.verticalScrollBar().value()
            horizontal = self._results.horizontalScrollBar().value()
            self._results.setHtml(
                self._build_results_html(self._results.toPlainText().splitlines())
            )
            cursor = self._results.textCursor()
            cursor.setPosition(anchor)
            cursor.setPosition(position, cursor.MoveMode.KeepAnchor)
            self._results.setTextCursor(cursor)
            self._results.verticalScrollBar().setValue(vertical)
            self._results.horizontalScrollBar().setValue(horizontal)

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
        was_modified = self._editor.document().isModified()
        if not self._confirm_document_replacement():
            return
        if (
            was_modified
            and not self._editor.document().isModified()
            and self._active_file is not None
        ):
            try:
                same_file = Path(path).samefile(self._active_file)
            except OSError:
                same_file = Path(path).resolve() == Path(self._active_file).resolve()
            if same_file:
                self.statusBar().showMessage(
                    "El programa se guardó en esa ruta; elija otra para crear uno nuevo."
                )
                return
        try:
            Path(path).write_text("", encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._input_path = path
        self._active_file = path
        self._set_file_slot("input", "Compiscript", path)
        self._saved_text = ""
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
        if not self._confirm_document_replacement():
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
            self._editor.setFocus()

    def _load_into_editor(self, path: str) -> bool:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return False
        self._input_path = path
        self._saved_text = text
        self._editor.setPlainText(text)
        self._active_file = path
        self._document_changed()
        return True

    def _save_file(self) -> bool:
        if self._active_file is None:
            return self._save_file_as()
        try:
            Path(self._active_file).write_text(
                self._editor.toPlainText(), encoding="utf-8"
            )
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return False
        self._saved_text = self._editor.toPlainText()
        self._document_changed()
        self.statusBar().showMessage(f"Guardado: {self._active_file}")
        return True

    def _save_file_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar programa Compiscript",
            self._active_file or "",
            "Compiscript (*.cps)",
        )
        if not path:
            return False
        path = self._ensure_cps_suffix(path)
        try:
            Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return False
        self._input_path = path
        self._active_file = path
        self._set_file_slot("input", "Compiscript", path)
        self._saved_text = self._editor.toPlainText()
        self._document_changed()
        return True

    def _confirm_document_replacement(self) -> bool:
        """Permit replacing the buffer only after a successful user decision."""
        if not self._editor.document().isModified():
            return True
        choice = QMessageBox.warning(
            self, "Cambios sin guardar",
            "El programa tiene cambios sin guardar. ¿Desea guardarlos?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Save:
            return self._save_file()
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        """Keep unsaved work; stop MARS and wait for workers before Qt destroys them."""
        if not self._confirm_document_replacement():
            event.ignore()
            return
        self.shutdown_workers()
        event.accept()

    def shutdown_workers(self) -> None:
        """Cancel MARS (terminating Java) and wait for both workers to finish."""
        execution = self._execution_worker
        if execution is not None and execution.isRunning():
            execution.request_cancel()
            execution.wait()
        compilation = self._worker
        if compilation is not None and compilation.isRunning():
            compilation.wait()

    def _document_changed(self) -> None:
        """Invalidate results when the buffer or its document identity changes."""
        snapshot = (self._input_path, self._editor.toPlainText())
        modified = snapshot[1] != self._saved_text
        self._editor.document().setModified(modified)
        self.setWindowModified(modified)
        if snapshot == self._document_snapshot:
            return
        self._document_snapshot = snapshot
        self._document_revision += 1
        execution = self._execution_worker
        if execution is not None and execution.isRunning():
            # Its result belongs to the previous revision and will be discarded.
            execution.request_cancel()
        self._clear_results()
        self._tac_view.set_compilation(None)
        self._layout_panel.set_compilation(None)
        self.statusBar().showMessage("Documento modificado; compile para actualizar los resultados.")

    # ------------------------------------------------------------ compilation

    def _run_compilation(self) -> None:
        """Compila el contenido actual del editor, aunque no esté guardado."""
        if self._compiling() or self._executing():
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
        self._compile_pending = True
        worker.start()
        self._refresh_actions()

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
        self._mips_compilation = None
        self._mips_view.show_pending()
        self._physical_panel.show_pending()
        self._execution_panel.reset("Compile el programa vigente para poder ejecutarlo.")
        self._refresh_actions()

    def _compiling(self) -> bool:
        # A flag, not isRunning(): the result signal is queued after run() ends.
        return self._compile_pending

    def _executing(self) -> bool:
        return self._execution_worker is not None and self._execution_worker.isRunning()

    def _refresh_actions(self) -> None:
        """Compile, run, cancel and export depend on the current revision and workers."""
        compiling, executing = self._compiling(), self._executing()
        runnable = (
            self._mips_compilation is not None
            and self._mips_compilation.accepted
            and not compiling
            and not executing
        )
        exportable = self._mips_compilation is not None and self._mips_compilation.accepted
        for widget in (self._run_btn, self._compile_action):
            widget.setEnabled(not compiling and not executing)
        for widget in (self._execute_btn, self._run_mips_action,
                       self._execution_panel.run_button):
            widget.setEnabled(runnable)
        for widget in (self._cancel_btn, self._cancel_action,
                       self._execution_panel.cancel_button):
            widget.setEnabled(executing)
        self._export_mips_action.setEnabled(exportable)

    def _finish_run(self) -> None:
        self._refresh_actions()

    def _on_finished(self, bundle: dict) -> None:
        self._compile_pending = False
        revision = bundle.get("document_revision")
        if revision is not None and revision != self._document_revision:
            self._finish_run()
            self.statusBar().showMessage("Resultado descartado: el documento cambió durante la compilación.")
            return
        self._last_bundle = bundle
        self._mips_compilation = bundle.get("mips_compilation")
        self._render_bundle(bundle)
        self._finish_run()
        compilation = bundle["compilation"]
        mips_compilation = self._mips_compilation
        if mips_compilation is not None and mips_compilation.accepted:
            mips_stats = mips_compilation.mips.statistics
            self.statusBar().showMessage(
                f"Compilación aceptada: {compilation.intermediate_result.statistics['instructions']} "
                f"instrucciones TAC y {mips_stats['instructions']} MIPS "
                f"({mips_stats['spills']} derrames). Puede ejecutar en MARS."
            )
            self._tabs.setCurrentWidget(self._mips_view)
            return
        if compilation.accepted and mips_compilation is not None:
            self.statusBar().showMessage("TAC aceptado, pero la generación MIPS fue rechazada.")
            self._tabs.setCurrentWidget(self._summary)
            return
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
        self._compile_pending = False
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
            pixmap = load_tree_pixmap(image_path)
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
        mips_compilation = bundle.get("mips_compilation")
        self._mips_view.set_compilation(mips_compilation)
        self._physical_panel.set_compilation(mips_compilation)

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
        lines.extend(self._mips_summary(bundle.get("mips_compilation")))
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

    @staticmethod
    def _mips_summary(mips_compilation: object | None) -> list[str]:
        if mips_compilation is None:
            return []
        if mips_compilation.mips is None:
            return ["MIPS       : no generado (falló una fase anterior)"]
        if mips_compilation.accepted:
            stats = mips_compilation.mips.statistics
            return [
                "MIPS       : ACCEPT (ensamblador completo para MARS 4.5)",
                f"Estadísticas MIPS: {stats['instructions']} instrucciones, "
                f"{stats['frames']} frames, {stats['stack_bytes']} bytes de pila, "
                f"{stats['spills']} derrames, {stats['reloads']} recargas",
            ]
        stage = STAGE_NAMES_MIPS["mips"]
        return [
            "MIPS       : ERRORES DE GENERACIÓN",
            *mips_diagnostic_lines(mips_compilation),
            f"Resultado  : REJECT — fase {stage}; sin ensamblador",
        ]

    # -------------------------------------------------------------- execution

    def _run_execution(self) -> None:
        """Ejecuta en MARS solo el MIPS de la revisión vigente (IDE-03, IDE-04)."""
        compilation = self._mips_compilation
        if compilation is None or not compilation.accepted or self._compiling() or self._executing():
            return
        from src.mips_consumer import default_mars_config

        try:
            config = default_mars_config()
        except ValueError as exc:
            self._execution_panel.reset(f"Configuración de MARS inválida: {exc}")
            return
        self._execution_panel.set_jar(config.jar)
        self._execution_panel.show_running()
        worker = ExecutionWorker(compilation.mips.assembly, config, self._document_revision)
        worker.completed.connect(self._on_execution_finished)
        self._execution_worker = worker
        worker.start()
        self._refresh_actions()
        self._tabs.setCurrentWidget(self._execution_panel)
        self.statusBar().showMessage("Ejecutando en MARS…")

    def _cancel_execution(self) -> None:
        worker = self._execution_worker
        if worker is not None and worker.isRunning():
            worker.request_cancel()
            self.statusBar().showMessage("Cancelando la ejecución de MARS…")

    def _on_execution_finished(self, result: object, revision: int) -> None:
        worker = self._execution_worker
        if worker is not None and worker.isRunning():
            worker.wait()
        self._refresh_actions()
        if revision != self._document_revision or self._mips_compilation is None:
            self.statusBar().showMessage(
                "Ejecución descartada: el documento cambió mientras se ejecutaba."
            )
            return
        self._execution_panel.set_result(result)
        self._refresh_actions()
        from src.mips_consumer import execution_summary

        self.statusBar().showMessage(f"MARS: {execution_summary(result)}")

    def _export_mips(self) -> None:
        compilation = self._mips_compilation
        if compilation is None or not compilation.accepted or not self._mips_view.has_tac():
            QMessageBox.information(
                self, "Sin MIPS", "Compile un programa válido antes de exportar el ensamblador."
            )
            return
        suggested = (
            str(Path(self._input_path).with_suffix(".asm")) if self._input_path else ""
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar ensamblador MIPS", suggested, "MIPS (*.asm *.s);;Texto (*.txt)"
        )
        if not path:
            return
        if compilation is not self._mips_compilation:
            self.statusBar().showMessage("Exportación cancelada: el documento cambió.")
            return
        try:
            target = self._mips_view.export(path)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se exportó el ensamblador: {exc}")
            return
        self.statusBar().showMessage(f"MIPS exportado: {target}")

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
                or "ERROR:" in line
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
        self._mips_view.set_compilation(None)
        self._physical_panel.set_compilation(None)
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


__all__ = ["CompilationWorker", "ExecutionWorker", "MainWindow", "launch_gui"]
