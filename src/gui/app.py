from __future__ import annotations
import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTabWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QMessageBox, QGroupBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QListWidget, QListWidgetItem, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont, QPixmap, QColor, QTextCharFormat, QTextCursor

from src.gui.theme import Palette, LIGHT, DARK, stylesheet
from src.gui.parse_tree_view import build_tree_widget
from src.gui.semantic_results import SemanticResultsPanel


class StepViewer(QWidget):
    """Navegador paso a paso del proceso de parseo (shift/reduce/expand)."""

    def __init__(self, steps: list, palette: Palette, mode: str = "LR", parent=None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._mode = mode
        self._palette = palette
        self._current = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        nav = QHBoxLayout()
        self._btn_first = QPushButton("First")
        self._btn_prev  = QPushButton("Prev")
        self._btn_next  = QPushButton("Next")
        self._btn_last  = QPushButton("Last")
        self._lbl_step  = QLabel()
        for btn in (self._btn_first, self._btn_prev, self._btn_next, self._btn_last):
            btn.setFixedWidth(80)
        self._btn_first.clicked.connect(lambda: self._goto(0))
        self._btn_prev.clicked.connect(lambda: self._goto(self._current - 1))
        self._btn_next.clicked.connect(lambda: self._goto(self._current + 1))
        self._btn_last.clicked.connect(lambda: self._goto(len(self._steps) - 1))
        nav.addWidget(self._btn_first)
        nav.addWidget(self._btn_prev)
        nav.addWidget(self._lbl_step)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_last)
        nav.addStretch()
        layout.addLayout(nav)

        if self._mode == "LR":
            headers = ["Stack (states)", "Symbols", "Remaining Input", "Action"]
        else:
            headers = ["Parse Stack", "Remaining Input", "Action"]

        self._table = QTableWidget(len(self._steps), len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setFont(QFont("Cascadia Mono", 9))

        for row, step in enumerate(self._steps):
            if self._mode == "LR":
                cells = [str(step.stack), str(step.symbols), str(step.remaining), step.action_taken]
            else:
                cells = [str(step.stack), str(step.remaining), step.action_taken]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(row, col, item)

        layout.addWidget(self._table)
        self._update()

    def _goto(self, idx: int) -> None:
        if 0 <= idx < len(self._steps):
            self._current = idx
            self._update()

    def _update(self) -> None:
        n = len(self._steps)
        self._lbl_step.setText(f"  Step {self._current + 1} / {n}  ")
        self._btn_first.setEnabled(self._current > 0)
        self._btn_prev.setEnabled(self._current > 0)
        self._btn_next.setEnabled(self._current < n - 1)
        self._btn_last.setEnabled(self._current < n - 1)

        hl = QColor(self._palette.row_highlight)
        base = QColor(self._palette.surface)
        for row in range(n):
            bg = hl if row == self._current else base
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item:
                    item.setBackground(bg)

        self._table.scrollTo(
            self._table.model().index(self._current, 0),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )


class AnalysisWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, yalex_path: str, yapar_path: str, input_text: str) -> None:
        super().__init__()
        self.yalex_path = yalex_path
        self.yapar_path = yapar_path
        self.input_text = input_text

    def run(self) -> None:
        try:
            from src.parser.yapar_scanner import YAParScanner, build_grammar
            from src.parser.string_analyzer import StringAnalyzer
            from src.parser.tokenizer_bridge import tokenize_with_spans
            from src.utils.visualizer import render_lr0_automaton

            grammar = build_grammar(YAParScanner(self.yapar_path).scan())
            analyzer = StringAnalyzer(grammar)
            lines = [l.strip() for l in self.input_text.splitlines() if l.strip()]
            results = []
            for line in lines:
                try:
                    toks, spans = tokenize_with_spans(self.yalex_path, line)
                    results.append(analyzer.analyze(toks, spans=spans, input_text=line))
                except Exception as lex_err:
                    from src.parser.string_analyzer import AnalysisResult
                    from src.parser.slr1 import ParseResult
                    results.append(AnalysisResult(
                        input_string=line,
                        tokens=[],
                        slr1_result=ParseResult(accepted=False, steps=[], error=f"Lex error: {lex_err}"),
                        lalr_result=ParseResult(accepted=False, steps=[], error=f"Lex error: {lex_err}"),
                        ll1_result=None,
                        ll1_error=f"Lex error: {lex_err}",
                    ))

            lr0_path = render_lr0_automaton(analyzer.automaton, 'output/lr0')
            self.finished.emit({
                'analyzer': analyzer,
                'results': results,
                'lr0_image': lr0_path,
                'grammar': grammar,
            })
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


class AntlrAnalysisWorker(QThread):
    """Generate and execute a selected .g4 grammar outside the GUI thread."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, grammar_path: str, start_rule: str, input_text: str) -> None:
        super().__init__()
        self.grammar_path = grammar_path
        self.start_rule = start_rule
        self.input_text = input_text

    def run(self) -> None:
        try:
            from src.antlr_mode.runner import AntlrModeError, analyze_with_g4
            from src.utils.visualizer import render_parse_tree

            result = analyze_with_g4(
                self.grammar_path,
                self.input_text,
                self.start_rule,
            )
            tree_image = None
            tree_error = None
            if result.tree is not None:
                try:
                    output_name = result.generated_directory.name
                    tree_image = render_parse_tree(
                        result.tree,
                        f"output/antlr/tree-{output_name}",
                    )
                except Exception as exc:
                    tree_error = str(exc)
            self.finished.emit({
                "mode": "antlr",
                "result": result,
                "tree_image": tree_image,
                "tree_error": tree_error,
            })
        except AntlrModeError as exc:
            self.error.emit(str(exc))
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


class SemanticAnalysisWorker(QThread):
    """Run syntax + semantics (Nelson's extended registry) off the GUI thread.

    Used only when a semantic profile is loaded alongside a ``.g4`` grammar
    (IDE-04, IDE-08); with no profile loaded the existing
    :class:`AntlrAnalysisWorker` path (syntax only) is unaffected.
    """

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
        try:
            from src.antlr_mode.runner import AntlrModeError
            from src.gui.semantic_bridge import (
                SemanticBridgeError,
                analyze_semantics_with_extensions,
            )
            from src.utils.visualizer import render_parse_tree

            result = analyze_semantics_with_extensions(
                self.grammar_path,
                self.input_text,
                self.profile_path,
                self.start_rule,
                self.source_path,
            )
            tree_image = None
            tree_error = None
            syntax_result = result.syntax_result
            if syntax_result.tree is not None:
                try:
                    output_name = syntax_result.generated_directory.name
                    tree_image = render_parse_tree(
                        syntax_result.tree,
                        f"output/antlr/tree-{output_name}",
                    )
                except Exception as exc:
                    tree_error = str(exc)
            self.finished.emit({
                "mode": "semantic",
                "result": syntax_result,
                "semantic_result": result.semantic_result,
                "tree_image": tree_image,
                "tree_error": tree_error,
            })
        except (AntlrModeError, SemanticBridgeError) as exc:
            self.error.emit(str(exc))
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YAPar IDE — Syntactic Analyzer Generator")
        self.setMinimumSize(1320, 820)

        self._yalex_path: str | None = None
        self._yapar_path: str | None = None
        self._g4_path: str | None = None
        self._input_path: str | None = None
        self._profile_path: str | None = None
        self._active_file: str | None = None
        self._worker: AnalysisWorker | AntlrAnalysisWorker | SemanticAnalysisWorker | None = None
        self._last_bundle: dict | None = None

        self._palette: Palette = LIGHT
        self._build_menu()
        self._build_ui()
        self._apply_theme(LIGHT)

    # ── Theming ───────────────────────────────────────────────────────────

    def _apply_theme(self, p: Palette) -> None:
        self._palette = p
        QApplication.instance().setStyleSheet(stylesheet(p))
        self._theme_btn.setText("Light Mode" if p.name == "dark" else "Dark Mode")
        # re-render results if we have data
        if self._last_bundle is not None:
            self._render_bundle(self._last_bundle)

    def _toggle_theme(self) -> None:
        self._apply_theme(DARK if self._palette.name == "light" else LIGHT)

    # ── Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        for label, slot in [
            ("New .cps…", self._new_cps),
            ("Open .yalex…", self._open_yalex),
            ("Open .yapar…", self._open_yapar),
            ("Open .g4…", self._open_g4),
            ("Open Input…", self._open_input),
            ("Open Semantic Profile…", self._open_profile),
            ("Save Current File", self._save_file),
            ("Save As…", self._save_file_as),
        ]:
            a = QAction(label, self)
            a.triggered.connect(slot)
            fm.addAction(a)

        rm = mb.addMenu("&Run")
        ra = QAction("Analyze", self)
        ra.setShortcut("Ctrl+R")
        ra.triggered.connect(self._run_analysis)
        rm.addAction(ra)

        vm = mb.addMenu("&View")
        ta = QAction("Toggle Light / Dark", self)
        ta.setShortcut("Ctrl+T")
        ta.triggered.connect(self._toggle_theme)
        vm.addAction(ta)

    # ── UI build ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        c = QWidget()
        self.setCentralWidget(c)
        root = QVBoxLayout(c)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Top toolbar
        bar = QHBoxLayout()
        bar.setSpacing(6)
        for text, slot in [
            ("Open YALex", self._open_yalex),
            ("Open YAPar", self._open_yapar),
            ("Open G4", self._open_g4),
            ("Open Input", self._open_input),
            ("Save", self._save_file),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(32)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()

        bar.addWidget(QLabel("Mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("YALex + YAPar", "yapar")
        self._mode_combo.addItem("ANTLR (.g4)", "antlr")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        bar.addWidget(self._mode_combo)

        bar.addWidget(QLabel("Start:"))
        self._start_rule_combo = QComboBox()
        self._start_rule_combo.setMinimumWidth(130)
        self._start_rule_combo.setEnabled(False)
        self._start_rule_combo.setToolTip(
            "Regla de parser desde la que ANTLR comienza el análisis."
        )
        bar.addWidget(self._start_rule_combo)

        self._profile_btn = QPushButton("Load Profile")
        self._profile_btn.setToolTip(
            "Cargar un perfil semántico JSON (opcional) para compilar .cps con análisis semántico."
        )
        self._profile_btn.clicked.connect(self._open_profile)
        bar.addWidget(self._profile_btn)
        self._profile_label = QLabel("Profile: none")
        self._profile_label.setObjectName("sectionTitle")
        bar.addWidget(self._profile_label)

        self._theme_btn = QPushButton("Dark Mode")
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.clicked.connect(self._toggle_theme)
        bar.addWidget(self._theme_btn)

        self._run_btn = QPushButton("Analyze  (Ctrl+R)")
        self._run_btn.setObjectName("analyzeBtn")
        self._run_btn.setFixedHeight(32)
        self._run_btn.clicked.connect(self._run_analysis)
        bar.addWidget(self._run_btn)
        root.addLayout(bar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left panel: clickable loaded files ──
        left = QGroupBox("Loaded Files")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 14, 10, 10)
        ll.setSpacing(6)

        hint = QLabel("Click to view in editor")
        hint.setObjectName("sectionTitle")
        ll.addWidget(hint)

        self._file_list = QListWidget()
        self._file_list.setIconSize(QSize(16, 16))
        self._file_list.itemClicked.connect(self._on_file_clicked)
        ll.addWidget(self._file_list)

        # Build empty rows for the supported input slots
        self._file_items: dict[str, QListWidgetItem] = {}
        for key, label in [
            ("yalex", "YALex: none"),
            ("yapar", "YAPar: none"),
            ("g4", "ANTLR G4: none"),
            ("input", "Input: none"),
        ]:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, None)
            self._file_list.addItem(it)
            self._file_items[key] = it

        ll.addStretch()
        left.setMinimumWidth(240)
        left.setMaximumWidth(320)
        splitter.addWidget(left)

        # ── Right tabs ──
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._editor = QTextEdit()
        self._editor.setFont(QFont("Cascadia Mono", 10))
        self._tabs.addTab(self._editor, "Editor")

        # LR(0) tab — image + open-externally button
        lr0_container = QWidget()
        lr0_layout = QVBoxLayout(lr0_container)
        lr0_layout.setContentsMargins(4, 4, 4, 4)
        lr0_layout.setSpacing(6)

        lr0_bar = QHBoxLayout()
        self._lr0_info = QLabel("Run analysis to see LR(0) automaton.")
        self._lr0_info.setObjectName("sectionTitle")
        lr0_bar.addWidget(self._lr0_info)
        lr0_bar.addStretch()
        self._lr0_open_btn = QPushButton("Open image externally")
        self._lr0_open_btn.setEnabled(False)
        self._lr0_open_btn.clicked.connect(self._open_lr0_externally)
        lr0_bar.addWidget(self._lr0_open_btn)
        lr0_layout.addLayout(lr0_bar)

        self._lr0_img = QLabel()
        self._lr0_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc = QScrollArea()
        sc.setWidget(self._lr0_img)
        sc.setWidgetResizable(True)
        lr0_layout.addWidget(sc, 1)
        self._lr0_image_path: str | None = None
        self._tabs.addTab(lr0_container, "LR(0)")

        self._table_tabs = QTabWidget()
        self._tabs.addTab(self._table_tabs, "Tables")

        self._tree_tabs = QTabWidget()
        self._tabs.addTab(self._tree_tabs, "Parse Tree")

        self._semantic_panel = SemanticResultsPanel()
        self._tabs.addTab(self._semantic_panel, "Semantics")

        self._steps_tabs = QTabWidget()
        self._tabs.addTab(self._steps_tabs, "Steps")

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setFont(QFont("Cascadia Mono", 10))
        self._tabs.addTab(self._results, "Results")

        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1060])
        root.addWidget(splitter, 1)

        self.statusBar().showMessage("Ready — load YALex, YAPar, and input files, then press Analyze.")

    # ── File handling ─────────────────────────────────────────────────────

    def _set_file_slot(self, key: str, label_prefix: str, path: str) -> None:
        it = self._file_items[key]
        it.setText(f"{label_prefix}: {os.path.basename(path)}")
        it.setToolTip(path)
        it.setData(Qt.ItemDataRole.UserRole, path)

    def _on_file_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            self._load_into_editor(path)

    def _load_into_editor(self, path: str) -> None:
        try:
            with open(path, encoding='utf-8') as f:
                self._editor.setPlainText(f.read())
        except Exception as e:
            QMessageBox.warning(self, "Read error", f"Could not read {path}\n\n{e}")
            return
        self._editor.setExtraSelections([])
        self._active_file = path
        self._tabs.setCurrentIndex(0)
        self.statusBar().showMessage(f"Loaded {path}")

    def _open_yalex(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Open YALex", "", "YALex (*.yal *.yalex);;All (*)")
        if p:
            self._yalex_path = p
            self._set_mode("yapar")
            self._set_file_slot("yalex", "YALex", p)
            self._load_into_editor(p)

    def _open_yapar(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Open YAPar", "", "YAPar (*.yapar *.yalp);;All (*)")
        if p:
            self._yapar_path = p
            self._set_mode("yapar")
            self._set_file_slot("yapar", "YAPar", p)
            self._load_into_editor(p)

    def _open_g4(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Open ANTLR Grammar",
            "",
            "ANTLR Grammar (*.g4);;All (*)",
        )
        if not p:
            return
        try:
            self._load_g4_rules(p)
        except Exception as exc:
            QMessageBox.warning(self, "Invalid ANTLR grammar", str(exc))
            return
        self._g4_path = p
        self._set_mode("antlr")
        self._set_file_slot("g4", "ANTLR G4", p)
        self._load_into_editor(p)

    def _load_g4_rules(self, path: str) -> None:
        from src.antlr_mode.grammar_info import inspect_g4

        info = inspect_g4(path)
        self._start_rule_combo.clear()
        self._start_rule_combo.addItems(info.parser_rules)
        self._start_rule_combo.setCurrentText(info.default_start_rule)
        self._start_rule_combo.setToolTip(
            f"{info.name}: {len(info.parser_rules)} regla(s) de parser."
        )

    def _set_mode(self, mode: str) -> None:
        index = self._mode_combo.findData(mode)
        if index >= 0:
            self._mode_combo.setCurrentIndex(index)

    def _on_mode_changed(self) -> None:
        is_antlr = self._mode_combo.currentData() == "antlr"
        self._start_rule_combo.setEnabled(is_antlr and self._start_rule_combo.count() > 0)
        if is_antlr:
            self.statusBar().showMessage(
                "ANTLR mode — load a .g4 grammar and an input file."
            )
        else:
            self.statusBar().showMessage(
                "YAPar mode — load YALex, YAPar, and input files."
            )

    def _open_input(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Open Input",
            "",
            "Source (*.txt *.cps);;All (*)",
        )
        if p:
            self._input_path = p
            self._set_file_slot("input", "Input", p)
            self._load_into_editor(p)

    def _new_cps(self) -> None:
        """Create a new, empty .cps file and load it into the editor (IDE-01/02)."""
        p, _ = QFileDialog.getSaveFileName(self, "New Compiscript file", "programa.cps", "Compiscript (*.cps)")
        if not p:
            return
        if not p.endswith(".cps"):
            p += ".cps"
        with open(p, "w", encoding="utf-8") as f:
            f.write("")
        self._input_path = p
        self._active_file = p
        self._set_file_slot("input", "Input", p)
        self._editor.setPlainText("")
        self._editor.setExtraSelections([])
        self._tabs.setCurrentIndex(0)
        self.statusBar().showMessage(f"Created {p}")

    def _open_profile(self) -> None:
        """Load an optional semantic profile JSON (IDE-04)."""
        p, _ = QFileDialog.getOpenFileName(
            self, "Open Semantic Profile", "", "Semantic profile (*.json);;All (*)"
        )
        if not p:
            return
        try:
            from src.semantic.profile import load_profile

            profile = load_profile(p)
        except Exception as exc:
            QMessageBox.warning(self, "Invalid semantic profile", str(exc))
            return
        self._profile_path = p
        self._profile_label.setText(f"Profile: {profile.name}")
        self.statusBar().showMessage(f"Loaded semantic profile {os.path.basename(p)}")

    def _save_file_as(self) -> None:
        """Save the editor's contents to a new path without losing the extension."""
        default_ext = ".cps" if (self._active_file or "").endswith(".cps") else ""
        p, _ = QFileDialog.getSaveFileName(
            self, "Save As", self._active_file or f"programa{default_ext}",
            "Compiscript (*.cps);;All (*)",
        )
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(self._editor.toPlainText())
        self._active_file = p
        if p.endswith(".cps") or p == self._input_path:
            self._input_path = p
            self._set_file_slot("input", "Input", p)
        self.statusBar().showMessage(f"Saved {p}")

    def _save_file(self) -> None:
        if not self._active_file:
            QMessageBox.information(self, "Save", "No file active in editor.")
            return
        with open(self._active_file, 'w', encoding='utf-8') as f:
            f.write(self._editor.toPlainText())
        if self._active_file == self._g4_path:
            try:
                self._load_g4_rules(self._g4_path)
            except Exception as exc:
                QMessageBox.warning(self, "Invalid ANTLR grammar", str(exc))
        self.statusBar().showMessage(f"Saved {self._active_file}")

    # ── Analysis ──────────────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        if self._mode_combo.currentData() == "antlr":
            if self._profile_path:
                self._run_semantic_analysis()
            else:
                self._run_antlr_analysis()
            return
        if not self._yalex_path or not self._yapar_path or not self._input_path:
            QMessageBox.warning(self, "Missing Files", "Load .yalex, .yapar, and input file first.")
            return
        with open(self._input_path, encoding='utf-8') as f:
            text = f.read()
        self._run_btn.setEnabled(False)
        self.statusBar().showMessage("Analyzing…")
        self._worker = AnalysisWorker(self._yalex_path, self._yapar_path, text)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _run_antlr_analysis(self) -> None:
        start_rule = self._start_rule_combo.currentText()
        if not self._g4_path or not self._input_path or not start_rule:
            QMessageBox.warning(
                self,
                "Missing Files",
                "Load a .g4 grammar, select its start rule, and load an input file.",
            )
            return
        with open(self._input_path, encoding="utf-8") as source_file:
            text = source_file.read()
        self._run_btn.setEnabled(False)
        self.statusBar().showMessage(
            "Generating ANTLR parser and analyzing… First use may download ANTLR."
        )
        self._worker = AntlrAnalysisWorker(self._g4_path, start_rule, text)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _run_semantic_analysis(self) -> None:
        """Compile a .cps with syntax + semantics (IDE-04), off the GUI thread."""
        start_rule = self._start_rule_combo.currentText()
        if not self._g4_path or not self._input_path or not start_rule:
            QMessageBox.warning(
                self,
                "Missing Files",
                "Load a .g4 grammar, select its start rule, and load an input file.",
            )
            return
        if not self._profile_path:
            QMessageBox.warning(self, "Missing Profile", "Load a semantic profile first.")
            return
        with open(self._input_path, encoding="utf-8") as source_file:
            text = source_file.read()
        self._run_btn.setEnabled(False)
        self.statusBar().showMessage("Compiling (syntax + semantics)…")
        self._worker = SemanticAnalysisWorker(
            self._g4_path, self._profile_path, start_rule, text, self._input_path
        )
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, bundle: dict) -> None:
        self._run_btn.setEnabled(True)
        mode_label = {"antlr": "ANTLR", "semantic": "Compiscript"}.get(
            bundle.get("mode"), "YAPar"
        )
        self.statusBar().showMessage(f"{mode_label} analysis complete.")
        self._last_bundle = bundle
        self._render_bundle(bundle)

    def _load_lr0_image(self, path: str, state_count: int) -> None:
        self._lr0_image_path = path if os.path.exists(path) else None
        self._lr0_open_btn.setEnabled(self._lr0_image_path is not None)

        if not self._lr0_image_path:
            self._lr0_img.setText("LR(0) image not available.")
            self._lr0_img.setPixmap(QPixmap())
            self._lr0_info.setText("No image generated.")
            return

        size_mb = os.path.getsize(path) / (1024 * 1024)
        px = QPixmap(path)
        if px.isNull():
            self._lr0_img.setPixmap(QPixmap())
            self._lr0_img.setText(
                f"Image too large to render in-app ({size_mb:.1f} MB).\n"
                f"Use 'Open image externally' button above."
            )
            self._lr0_info.setText(
                f"{state_count} states  |  image {size_mb:.1f} MB (rendered, view externally)"
            )
            return

        # Scale down if too wide to keep GUI responsive
        viewport_w = max(self.width() - 320, 800)
        if px.width() > viewport_w * 2:
            px = px.scaledToWidth(viewport_w * 2, Qt.TransformationMode.SmoothTransformation)
        self._lr0_img.setPixmap(px)
        self._lr0_img.adjustSize()
        self._lr0_info.setText(
            f"{state_count} states  |  image {px.width()}x{px.height()} px"
        )

    def _open_lr0_externally(self) -> None:
        if not self._lr0_image_path:
            return
        try:
            os.startfile(self._lr0_image_path)  # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", self._lr0_image_path])

    def _render_bundle(self, bundle: dict) -> None:
        if bundle.get("mode") == "semantic":
            self._render_semantic_bundle(bundle)
            return
        if bundle.get("mode") == "antlr":
            self._render_antlr_bundle(bundle)
            return
        from src.utils.visualizer import render_parse_tree

        img = bundle['lr0_image']
        self._load_lr0_image(img, len(bundle['analyzer'].automaton.states))

        analyzer = bundle['analyzer']
        self._table_tabs.clear()
        self._add_first_follow_table(analyzer)
        self._add_parse_table("SLR(1)", analyzer.slr1_table)
        self._add_parse_table("LALR", analyzer.lalr_table)
        self._add_productions_table(analyzer.slr1_table.grammar)
        self._add_ll1_table(analyzer.ll1_table, analyzer.ll1_conflicts)

        self._tree_tabs.clear()
        for i, r in enumerate(bundle['results'], 1):
            accepted = r.slr1_result and r.slr1_result.accepted
            tab_label = f"[{i:02d}] {'OK' if accepted else 'FAIL'}"
            sc = QScrollArea()
            sc.setWidgetResizable(True)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tree = (r.slr1_result.tree if r.slr1_result else None) or \
                   (r.lalr_result.tree if r.lalr_result else None) or \
                   (r.ll1_result.tree if r.ll1_result else None)
            if accepted and tree is not None:
                try:
                    tree_path = render_parse_tree(tree, f"output/tree_{i:02d}")
                    if os.path.exists(tree_path):
                        px = QPixmap(tree_path)
                        lbl.setPixmap(px)
                        lbl.adjustSize()
                    else:
                        lbl.setText("Tree image could not be rendered.")
                except Exception as exc:
                    lbl.setText(f"Tree render error: {exc}")
            else:
                lbl.setText("String rejected — no parse tree available.")
            sc.setWidget(lbl)
            self._tree_tabs.addTab(sc, tab_label)

        self._steps_tabs.clear()
        for i, r in enumerate(bundle['results'], 1):
            accepted = r.slr1_result and r.slr1_result.accepted
            tab_label = f"[{i:02d}] {'OK' if accepted else 'FAIL'}"
            steps = (r.slr1_result.steps if r.slr1_result and r.slr1_result.steps else
                     r.lalr_result.steps if r.lalr_result and r.lalr_result.steps else [])
            if steps:
                viewer = StepViewer(steps, palette=self._palette, mode="LR")
                self._steps_tabs.addTab(viewer, tab_label)
            elif r.ll1_result and r.ll1_result.steps:
                viewer = StepViewer(r.ll1_result.steps, palette=self._palette, mode="LL")
                self._steps_tabs.addTab(viewer, tab_label)
            else:
                lbl = QLabel("No steps available.")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._steps_tabs.addTab(lbl, tab_label)

        lines: list[str] = []
        lines.append(f"{'=' * 70}")
        lines.append(f"  ANALYSIS RESULTS")
        lines.append(f"{'=' * 70}")

        slr_conflicts = analyzer.slr1_table.conflicts
        lalr_conflicts = analyzer.lalr_table.conflicts
        if slr_conflicts:
            lines.append("\n[!] SLR(1) conflicts detected:")
            for c in slr_conflicts:
                lines.append(f"    {c}")
        if lalr_conflicts:
            lines.append("\n[!] LALR conflicts detected:")
            for c in lalr_conflicts:
                lines.append(f"    {c}")
        if analyzer.ll1_conflicts:
            lines.append(
                f"\n[!] LL(1): {len(analyzer.ll1_conflicts)} conflict(s) "
                f"resolved by definition order (first wins):"
            )
            for c in analyzer.ll1_conflicts[:8]:
                lines.append(f"    {c}")
            if len(analyzer.ll1_conflicts) > 8:
                lines.append(f"    … and {len(analyzer.ll1_conflicts) - 8} more")

        lines.append("")
        for i, r in enumerate(bundle['results'], 1):
            slr_ok = r.slr1_result and r.slr1_result.accepted
            lalr_ok = r.lalr_result and r.lalr_result.accepted
            ll1_ok = r.ll1_result is not None and r.ll1_result.accepted
            slr  = "ACCEPT" if slr_ok  else "REJECT"
            lalr = "ACCEPT" if lalr_ok else "REJECT"
            ll1  = "N/A" if r.ll1_result is None else ("ACCEPT" if ll1_ok else "REJECT")
            lines.append(f"[{i:02d}] {r.input_string}")
            lines.append(f"      Tokens : {r.tokens}")
            lines.append(f"      SLR(1) : {slr}  |  LALR: {lalr}  |  LL(1): {ll1}")
            if not slr_ok:
                err = (r.slr1_result.error if r.slr1_result else None) or \
                      (r.lalr_result.error if r.lalr_result else None)
                if err:
                    lines.append(f"      [!] Error : {err}")
            lines.append("")

        self._highlight_input_results(bundle['results'])
        html = self._build_results_html(lines)
        self._results.setHtml(html)
        self._tabs.setCurrentIndex(5)

    def _render_antlr_bundle(self, bundle: dict) -> None:
        result = bundle["result"]
        self._lr0_image_path = None
        self._lr0_open_btn.setEnabled(False)
        self._lr0_img.setPixmap(QPixmap())
        self._lr0_img.setText(
            "LR(0) belongs to the YAPar mode.\n"
            "ANTLR uses its own adaptive prediction engine."
        )
        self._lr0_info.setText("ANTLR mode — YAPar automaton remains unchanged.")

        self._table_tabs.clear()
        tokens = result.tokens
        token_table = QTableWidget(len(tokens), 5)
        token_table.setHorizontalHeaderLabels(
            ["#", "Type", "Text", "Line", "Column"]
        )
        token_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        token_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        token_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        token_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        token_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        token_table.verticalHeader().setVisible(False)
        token_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        token_table.setFont(QFont("Cascadia Mono", 9))
        for row, token in enumerate(tokens):
            values = [
                str(row),
                token.token_type,
                token.text,
                str(token.line),
                str(token.column),
            ]
            for column, value in enumerate(values):
                token_table.setItem(row, column, QTableWidgetItem(value))
        self._table_tabs.addTab(token_table, "ANTLR Tokens")

        self._tree_tabs.clear()
        tree_container = QScrollArea()
        tree_container.setWidgetResizable(True)
        tree_label = QLabel()
        tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_path = bundle.get("tree_image")
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                tree_label.setText("The ANTLR tree image could not be loaded.")
            else:
                tree_label.setPixmap(pixmap)
                tree_label.adjustSize()
        elif bundle.get("tree_error"):
            tree_label.setText(f"Tree render error: {bundle['tree_error']}")
        else:
            tree_label.setText("No parse tree was produced.")
        tree_container.setWidget(tree_label)
        self._tree_tabs.addTab(
            tree_container,
            "ACCEPT" if result.accepted else "WITH ERRORS",
        )

        self._steps_tabs.clear()
        steps_note = QLabel(
            "Shift/reduce and LL(1) steps belong to the YAPar engine.\n"
            "They remain available when the YALex + YAPar mode is selected."
        )
        steps_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._steps_tabs.addTab(steps_note, "ANTLR")

        lines = [
            "=" * 70,
            "  ANTLR ANALYSIS RESULTS",
            "=" * 70,
            f"Grammar   : {result.grammar.name}",
            f"File      : {result.grammar.path}",
            f"Start rule: {result.start_rule}",
            f"Tokens    : {len(result.tokens)}",
            f"Result    : {'ACCEPT' if result.accepted else 'WITH ERRORS'}",
            "",
        ]
        if result.diagnostics:
            lines.append("Diagnostics:")
            for diagnostic in result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.stage} {diagnostic.line}:"
                    f"{diagnostic.column} — {diagnostic.message}"
                )
        else:
            lines.append("No lexical or syntactic errors.")
        if bundle.get("tree_error"):
            lines.extend(["", f"[!] Tree render: {bundle['tree_error']}"])

        self._editor.setExtraSelections([])
        self._results.setHtml(self._build_results_html(lines))
        self._tabs.setCurrentIndex(5)

    def _render_semantic_bundle(self, bundle: dict) -> None:
        """Render syntax (reusing the ANTLR path) plus semantics (IDE-04..07).

        A navigable tree tab (``src/gui/parse_tree_view.py``) is appended
        here rather than inside ``_render_antlr_bundle`` itself, so the
        existing regression test that calls ``_render_antlr_bundle``
        directly and asserts ``_tree_tabs.count() == 1`` keeps passing.
        """
        result = bundle["result"]
        self._render_antlr_bundle({
            "mode": "antlr",
            "result": result,
            "tree_image": bundle.get("tree_image"),
            "tree_error": bundle.get("tree_error"),
        })
        if result.tree is not None:
            self._tree_tabs.addTab(build_tree_widget(result.tree), "Navigable")

        semantic_result = bundle.get("semantic_result")
        self._semantic_panel.set_result(semantic_result)

        lines = [
            "=" * 70,
            "  COMPISCRIPT SEMANTIC ANALYSIS",
            "=" * 70,
            f"Grammar   : {result.grammar.name}",
            f"Profile   : {self._profile_path}",
            f"Start rule: {result.start_rule}",
        ]
        if not result.accepted:
            lines.append("Result    : SYNTAX ERRORS — semantics did not run.")
            for diagnostic in result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.stage} {diagnostic.line}:"
                    f"{diagnostic.column} — {diagnostic.message}"
                )
        elif semantic_result is None:
            lines.append("Result    : semantic analysis did not run.")
        else:
            lines.append(
                f"Result    : {'ACCEPT' if semantic_result.accepted else 'WITH ERRORS'}"
            )
            lines.append(f"Diagnostics: {len(semantic_result.diagnostics)}")
            for diagnostic in semantic_result.diagnostics:
                lines.append(
                    f"[!] {diagnostic.severity.value} {diagnostic.category.value} "
                    f"{diagnostic.location.line}:{diagnostic.location.column} — "
                    f"{diagnostic.message}"
                )
        if bundle.get("tree_error"):
            lines.extend(["", f"[!] Tree render: {bundle['tree_error']}"])

        self._results.setHtml(self._build_results_html(lines))
        self._tabs.setCurrentIndex(self._tabs.indexOf(self._semantic_panel))

    def _build_results_html(self, lines: list[str]) -> str:
        import html as html_mod
        p = self._palette
        parts = [f'<pre style="font-family:Cascadia Mono,Courier New,monospace;font-size:10pt;color:{p.text};">']
        for line in lines:
            esc = html_mod.escape(line)
            if '[!]' in line or 'REJECT' in line:
                parts.append(f'<span style="color:{p.danger};">{esc}</span>')
            elif 'ACCEPT' in line:
                parts.append(f'<span style="color:{p.success};">{esc}</span>')
            elif line.startswith('[') and line[3:4] == ']':
                parts.append(f'<b>{esc}</b>')
            else:
                parts.append(esc)
            parts.append('\n')
        parts.append('</pre>')
        return ''.join(parts)

    def _on_error(self, tb: str) -> None:
        import html as html_mod
        self._run_btn.setEnabled(True)
        self.statusBar().showMessage("Error during analysis.")
        esc = html_mod.escape(tb)
        p = self._palette
        self._results.setHtml(
            f'<pre style="font-family:Cascadia Mono,Courier New,monospace;font-size:10pt;color:{p.danger};">'
            f'ERROR:\n{esc}</pre>'
        )
        self._tabs.setCurrentIndex(5)

    # ── Editor highlight ──────────────────────────────────────────────────

    def _highlight_input_results(self, results: list) -> None:
        """Color-code lines in input editor: green=accepted, red=rejected."""
        if self._active_file != self._input_path:
            return

        fmt_ok = QTextCharFormat()
        fmt_ok.setBackground(QColor(self._palette.edit_ok))

        fmt_err = QTextCharFormat()
        fmt_err.setBackground(QColor(self._palette.edit_err))
        fmt_err.setUnderlineColor(QColor(self._palette.danger))
        fmt_err.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)

        doc = self._editor.document()
        selections = []
        result_idx = 0

        for line_idx in range(doc.blockCount()):
            block = doc.findBlockByLineNumber(line_idx)
            if not block.isValid() or not block.text().strip():
                continue
            if result_idx >= len(results):
                break
            r = results[result_idx]
            accepted = r.slr1_result and r.slr1_result.accepted
            fmt = fmt_ok if accepted else fmt_err

            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            sel.cursor = QTextCursor(block)
            sel.cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selections.append(sel)
            result_idx += 1

        self._editor.setExtraSelections(selections)

    # ── Table builders (palette-aware) ────────────────────────────────────

    def _add_productions_table(self, grammar) -> None:
        p = self._palette
        prods = grammar.productions
        tw = QTableWidget(len(prods), 3)
        tw.setHorizontalHeaderLabels(["#", "Head", "Body"])
        tw.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tw.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tw.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tw.verticalHeader().setVisible(False)
        tw.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tw.setFont(QFont("Cascadia Mono", 9))

        for row, prod in enumerate(prods):
            body_str = " ".join(str(s) for s in prod.body) if prod.body else "ε"
            num_item = QTableWidgetItem(str(prod.index))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setBackground(QColor(p.cell_prod_num))
            head_item = QTableWidgetItem(prod.head.name)
            head_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            head_item.setBackground(QColor(p.cell_prod_head))
            body_item = QTableWidgetItem(body_str)
            body_item.setBackground(QColor(p.cell_prod_body))
            tw.setItem(row, 0, num_item)
            tw.setItem(row, 1, head_item)
            tw.setItem(row, 2, body_item)

        self._table_tabs.addTab(tw, "Productions")

    def _add_first_follow_table(self, analyzer) -> None:
        p = self._palette
        non_terms = sorted(analyzer.grammar.non_terminals, key=lambda s: s.name)
        tw = QTableWidget(len(non_terms), 2)
        tw.setHorizontalHeaderLabels(["FIRST", "FOLLOW"])
        tw.setVerticalHeaderLabels([nt.name for nt in non_terms])
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tw.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        for row, nt in enumerate(non_terms):
            first_syms = analyzer.first.get(nt, set())
            follow_syms = analyzer.follow.get(nt, set())
            first_str = "{ " + ", ".join(sorted(s.name for s in first_syms)) + " }"
            follow_str = "{ " + ", ".join(sorted(s.name for s in follow_syms)) + " }"

            fi = QTableWidgetItem(first_str)
            fi.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            fi.setBackground(QColor(p.cell_first))
            tw.setItem(row, 0, fi)

            fo = QTableWidgetItem(follow_str)
            fo.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            fo.setBackground(QColor(p.cell_follow))
            tw.setItem(row, 1, fo)

        self._table_tabs.addTab(tw, "FIRST / FOLLOW")

    def _add_parse_table(self, name: str, table) -> None:
        p = self._palette
        states = sorted({s for s, _ in table.action} | {s for s, _ in table.goto_table})
        terminals = sorted({t for _, t in table.action})
        non_terms = sorted({nt for _, nt in table.goto_table})
        cols = terminals + non_terms

        tw = QTableWidget(len(states), len(cols))
        tw.setHorizontalHeaderLabels(cols)
        tw.setVerticalHeaderLabels([str(s) for s in states])
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tw.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        col_idx = {c: i for i, c in enumerate(cols)}
        state_row = {s: i for i, s in enumerate(states)}

        for (s, sym), cell in table.action.items():
            row = state_row.get(s)
            col = col_idx.get(sym)
            if row is None or col is None:
                continue
            action_type, value = cell
            val = f"{action_type[0].upper()}{value}"
            item = QTableWidgetItem(val)
            bg = {
                "shift": p.cell_shift,
                "reduce": p.cell_reduce,
                "accept": p.cell_accept,
            }.get(action_type, p.surface)
            item.setBackground(QColor(bg))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if action_type == "reduce":
                prod = table.grammar.productions[value]
                item.setToolTip(f"R{value}: {prod}")
            elif action_type == "shift":
                item.setToolTip(f"Shift → state {value}")
            elif action_type == "accept":
                item.setToolTip("Accept")
            tw.setItem(row, col, item)

        for (s, nt), ns in table.goto_table.items():
            row = state_row.get(s)
            col = col_idx.get(nt)
            if row is None or col is None:
                continue
            item = QTableWidgetItem(str(ns))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QColor(p.cell_goto))
            item.setToolTip(f"GOTO({s}, {nt}) = {ns}")
            tw.setItem(row, col, item)

        if table.conflicts:
            tw.setToolTip("Conflicts: " + "; ".join(table.conflicts[:3]))

        self._table_tabs.addTab(tw, name)

    def _add_ll1_table(
        self,
        table: dict,
        conflicts: list[str] | None = None,
    ) -> None:
        p = self._palette
        conflicts = conflicts or []

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        if conflicts:
            banner = QLabel(
                f"<b>Not strict LL(1):</b> {len(conflicts)} conflict(s) "
                f"resolved by definition order (first production wins). "
                f"Hover any conflicting cell for details."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                f"background-color: {p.cell_reduce}; color: {p.text}; "
                f"border: 1px solid {p.warning}; border-radius: 6px; "
                f"padding: 8px 12px; font-size: 9pt;"
            )
            layout.addWidget(banner)

        non_terms = sorted({nt for nt, _ in table})
        terminals = sorted({t for _, t in table})
        tw = QTableWidget(len(non_terms), len(terminals))
        tw.setHorizontalHeaderLabels(terminals)
        tw.setVerticalHeaderLabels(non_terms)
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tw.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # collect conflicting cells for tooltip
        conflict_by_cell: dict[tuple[str, str], list[str]] = {}
        import re as _re
        for c in conflicts:
            m = _re.match(r"M\[([^,]+),([^\]]+)\]:\s*(.*)", c)
            if m:
                nt, t, msg = m.group(1), m.group(2), m.group(3)
                conflict_by_cell.setdefault((nt, t), []).append(msg)

        nt_idx = {nt: i for i, nt in enumerate(non_terms)}
        t_idx = {t: i for i, t in enumerate(terminals)}
        for (nt, t), prod in table.items():
            row = nt_idx.get(nt)
            col = t_idx.get(t)
            if row is None or col is None:
                continue
            item = QTableWidgetItem(repr(prod))
            cell_msgs = conflict_by_cell.get((nt, t))
            if cell_msgs:
                item.setBackground(QColor(p.cell_reduce))
                item.setToolTip("Conflict resolved:\n" + "\n".join(cell_msgs))
            else:
                item.setBackground(QColor(p.cell_shift))
            tw.setItem(row, col, item)

        layout.addWidget(tw, 1)
        self._table_tabs.addTab(container, "LL(1)")


def launch_gui() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
