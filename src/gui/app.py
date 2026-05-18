from __future__ import annotations
import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTabWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QMessageBox, QGroupBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QPixmap, QColor


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
            from src.parser.tokenizer_bridge import tokenize_input
            from src.utils.visualizer import render_lr0_automaton

            grammar = build_grammar(YAParScanner(self.yapar_path).scan())
            analyzer = StringAnalyzer(grammar)
            lines = [l.strip() for l in self.input_text.splitlines() if l.strip()]
            results = []
            for line in lines:
                try:
                    from src.parser.tokenizer_bridge import tokenize_with_spans
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YAPar IDE — Syntactic Analyzer Generator")
        self.setMinimumSize(1280, 800)
        self._yalex_path: str | None = None
        self._yapar_path: str | None = None
        self._input_path: str | None = None
        self._active_file: str | None = None
        self._worker: AnalysisWorker | None = None
        self._build_menu()
        self._build_ui()

    def _build_menu(self) -> None:
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        for label, slot in [
            ("Open .yalex…", self._open_yalex),
            ("Open .yapar…", self._open_yapar),
            ("Open Input…", self._open_input),
            ("Save Current File", self._save_file),
        ]:
            a = QAction(label, self)
            a.triggered.connect(slot)
            fm.addAction(a)
        rm = mb.addMenu("&Run")
        ra = QAction("Analyze", self)
        ra.setShortcut("Ctrl+R")
        ra.triggered.connect(self._run_analysis)
        rm.addAction(ra)

    def _build_ui(self) -> None:
        c = QWidget()
        self.setCentralWidget(c)
        root = QVBoxLayout(c)
        root.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        for text, slot in [
            ("Open YALex", self._open_yalex),
            ("Open YAPar", self._open_yapar),
            ("Open Input", self._open_input),
            ("Save", self._save_file),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(30)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()
        self._run_btn = QPushButton("▶  Analyze  (Ctrl+R)")
        self._run_btn.setFixedHeight(30)
        self._run_btn.setStyleSheet("background-color: #2d7a2d; color: white; font-weight: bold;")
        self._run_btn.clicked.connect(self._run_analysis)
        bar.addWidget(self._run_btn)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QGroupBox("Loaded Files")
        ll = QVBoxLayout(left)
        self._lbl_yalex = QLabel("YALex: none")
        self._lbl_yapar = QLabel("YAPar: none")
        self._lbl_input = QLabel("Input: none")
        for lbl in (self._lbl_yalex, self._lbl_yapar, self._lbl_input):
            lbl.setWordWrap(True)
            ll.addWidget(lbl)
        ll.addStretch()
        left.setFixedWidth(220)
        splitter.addWidget(left)

        self._tabs = QTabWidget()

        self._editor = QTextEdit()
        self._editor.setFont(QFont("Courier New", 10))
        self._tabs.addTab(self._editor, "Editor")

        self._lr0_img = QLabel("Run analysis to see LR(0) automaton.")
        self._lr0_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc = QScrollArea()
        sc.setWidget(self._lr0_img)
        sc.setWidgetResizable(True)
        self._tabs.addTab(sc, "LR(0)")

        self._table_tabs = QTabWidget()
        self._tabs.addTab(self._table_tabs, "Tables")

        self._tree_tabs = QTabWidget()
        self._tabs.addTab(self._tree_tabs, "Parse Tree")

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setFont(QFont("Courier New", 10))
        self._tabs.addTab(self._results, "Results")

        splitter.addWidget(self._tabs)
        splitter.setSizes([220, 1060])
        root.addWidget(splitter)
        self.statusBar().showMessage("Ready — load YALex, YAPar, and input files, then press Analyze.")

    def _load_into_editor(self, path: str) -> None:
        with open(path, encoding='utf-8') as f:
            self._editor.setPlainText(f.read())
        self._active_file = path
        self._tabs.setCurrentIndex(0)
        self.statusBar().showMessage(f"Loaded {path}")

    def _open_yalex(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Open YALex", "", "YALex (*.yal *.yalex);;All (*)")
        if p:
            self._yalex_path = p
            self._lbl_yalex.setText(f"YALex: {os.path.basename(p)}")
            self._load_into_editor(p)

    def _open_yapar(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Open YAPar", "", "YAPar (*.yapar *.yalp);;All (*)")
        if p:
            self._yapar_path = p
            self._lbl_yapar.setText(f"YAPar: {os.path.basename(p)}")
            self._load_into_editor(p)

    def _open_input(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Open Input", "", "Text (*.txt);;All (*)")
        if p:
            self._input_path = p
            self._lbl_input.setText(f"Input: {os.path.basename(p)}")
            self._load_into_editor(p)

    def _save_file(self) -> None:
        if not self._active_file:
            QMessageBox.information(self, "Save", "No file active in editor.")
            return
        with open(self._active_file, 'w', encoding='utf-8') as f:
            f.write(self._editor.toPlainText())
        self.statusBar().showMessage(f"Saved {self._active_file}")

    def _run_analysis(self) -> None:
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

    def _on_done(self, bundle: dict) -> None:
        from src.utils.visualizer import render_parse_tree

        self._run_btn.setEnabled(True)
        self.statusBar().showMessage("Analysis complete.")

        img = bundle['lr0_image']
        if os.path.exists(img):
            px = QPixmap(img)
            self._lr0_img.setPixmap(px)
            self._lr0_img.adjustSize()

        analyzer = bundle['analyzer']
        self._table_tabs.clear()
        self._add_first_follow_table(analyzer)
        self._add_parse_table("SLR(1)", analyzer.slr1_table)
        self._add_parse_table("LALR", analyzer.lalr_table)
        if analyzer.ll1_table:
            self._add_ll1_table(analyzer.ll1_table, bundle['grammar'])
        else:
            lbl = QLabel(f"LL(1) not available (grammar is not LL(1)):\n\n{analyzer.ll1_error}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            lbl.setWordWrap(True)
            lbl.setContentsMargins(12, 12, 12, 12)
            self._table_tabs.addTab(lbl, "LL(1)")

        self._tree_tabs.clear()
        for i, r in enumerate(bundle['results'], 1):
            accepted = r.slr1_result and r.slr1_result.accepted
            tab_label = f"[{i:02d}] {'✓' if accepted else '✗'}"
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

        lines: list[str] = []
        lines.append(f"{'=' * 70}")
        lines.append(f"  ANALYSIS RESULTS")
        lines.append(f"{'=' * 70}")

        slr_conflicts = analyzer.slr1_table.conflicts
        lalr_conflicts = analyzer.lalr_table.conflicts
        if slr_conflicts:
            lines.append(f"\n⚠ SLR(1) conflicts detected:")
            for c in slr_conflicts:
                lines.append(f"    {c}")
        if lalr_conflicts:
            lines.append(f"\n⚠ LALR conflicts detected:")
            for c in lalr_conflicts:
                lines.append(f"    {c}")
        if analyzer.ll1_error:
            lines.append(f"\n⚠ LL(1): {analyzer.ll1_error[:120]}")

        lines.append("")
        for i, r in enumerate(bundle['results'], 1):
            slr_ok = r.slr1_result and r.slr1_result.accepted
            lalr_ok = r.lalr_result and r.lalr_result.accepted
            ll1_ok = r.ll1_result is not None and r.ll1_result.accepted
            slr  = "ACCEPT ✓" if slr_ok  else "REJECT ✗"
            lalr = "ACCEPT ✓" if lalr_ok else "REJECT ✗"
            ll1  = "N/A" if r.ll1_result is None else ("ACCEPT ✓" if ll1_ok else "REJECT ✗")
            lines.append(f"[{i:02d}] {r.input_string}")
            lines.append(f"      Tokens : {r.tokens}")
            lines.append(f"      SLR(1) : {slr}  |  LALR: {lalr}  |  LL(1): {ll1}")
            if not slr_ok:
                err = (r.slr1_result.error if r.slr1_result else None) or \
                      (r.lalr_result.error if r.lalr_result else None)
                if err:
                    lines.append(f"      ⚠ Error : {err}")
            lines.append("")

        html = self._build_results_html(lines, bundle['results'])
        self._results.setHtml(html)
        self._tabs.setCurrentIndex(4)

    def _build_results_html(self, lines: list[str], results: list) -> str:
        import html as html_mod
        parts = ['<pre style="font-family:Courier New,monospace;font-size:10pt;">']
        for line in lines:
            esc = html_mod.escape(line)
            if '⚠' in line or 'REJECT' in line:
                parts.append(f'<span style="color:#cc0000;">{esc}</span>')
            elif 'ACCEPT' in line:
                parts.append(f'<span style="color:#1a7a1a;">{esc}</span>')
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
        self._results.setHtml(
            f'<pre style="font-family:Courier New,monospace;font-size:10pt;color:#cc0000;">'
            f'ERROR:\n{esc}</pre>'
        )
        self._tabs.setCurrentIndex(4)

    def _add_first_follow_table(self, analyzer) -> None:
        from src.parser.grammar import EPSILON_SYM
        non_terms = sorted(analyzer.grammar.non_terminals, key=lambda s: s.name)
        tw = QTableWidget(len(non_terms), 2)
        tw.setHorizontalHeaderLabels(["FIRST", "FOLLOW"])
        tw.setVerticalHeaderLabels([nt.name for nt in non_terms])
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tw.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        for row, nt in enumerate(non_terms):
            first_syms = analyzer.first.get(nt, set())
            follow_syms = analyzer.follow.get(nt, set())

            first_str = "{ " + ", ".join(
                sorted(s.name for s in first_syms)
            ) + " }"
            follow_str = "{ " + ", ".join(
                sorted(s.name for s in follow_syms)
            ) + " }"

            fi = QTableWidgetItem(first_str)
            fi.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            fi.setBackground(QColor("#EAF4FB"))
            tw.setItem(row, 0, fi)

            fo = QTableWidgetItem(follow_str)
            fo.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            fo.setBackground(QColor("#EAFAF1"))
            tw.setItem(row, 1, fo)

        self._table_tabs.addTab(tw, "FIRST / FOLLOW")

    def _add_parse_table(self, name: str, table) -> None:
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
            bg = {"shift": "#d4edda", "reduce": "#fff3cd", "accept": "#cce5ff"}.get(action_type, "#fff")
            item.setBackground(QColor(bg))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tw.setItem(row, col, item)

        for (s, nt), ns in table.goto_table.items():
            row = state_row.get(s)
            col = col_idx.get(nt)
            if row is None or col is None:
                continue
            item = QTableWidgetItem(str(ns))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tw.setItem(row, col, item)

        if table.conflicts:
            tw.setToolTip("⚠ Conflicts: " + "; ".join(table.conflicts[:3]))

        self._table_tabs.addTab(tw, name)

    def _add_ll1_table(self, table: dict, grammar) -> None:
        non_terms = sorted({nt for nt, _ in table})
        terminals = sorted({t for _, t in table})
        tw = QTableWidget(len(non_terms), len(terminals))
        tw.setHorizontalHeaderLabels(terminals)
        tw.setVerticalHeaderLabels(non_terms)
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tw.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        nt_idx = {nt: i for i, nt in enumerate(non_terms)}
        t_idx = {t: i for i, t in enumerate(terminals)}
        for (nt, t), prod in table.items():
            row = nt_idx.get(nt)
            col = t_idx.get(t)
            if row is None or col is None:
                continue
            item = QTableWidgetItem(repr(prod))
            item.setBackground(QColor("#d4edda"))
            tw.setItem(row, col, item)
        self._table_tabs.addTab(tw, "LL(1)")


def launch_gui() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
