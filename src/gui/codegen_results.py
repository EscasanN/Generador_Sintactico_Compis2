"""IDE views for the code-generation phase (OUT-03, OUT-04, OUT-05).

Only reads the public, immutable results of the pipeline
(``CompilationResult``/``IntermediateCodeResult`` from ``src/codegen/results.py``,
``SymbolLayoutTable.rows()`` and ``ActivationRecordLayout``). It never builds,
lowers or verifies IR: the GUI thread only presents what the worker produced.

* :class:`TacView` -- monospaced TAC with search, copy and ``.tac`` export.
* :class:`LayoutPanel` -- extended symbol table plus activation records.
* :class:`DiagnosticsTable` -- lexical, syntactic, semantic and IR diagnostics
  together, each with its phase, kind and source position.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QTextDocument
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Same text as ``python -m src.main --cps … --emit-tac`` (IDE and CLI share it).
from src.main import tac_document


STAGE_NAMES = {
    "syntax": "sintáctica",
    "semantic": "semántica",
    "codegen": "de generación de código",
}
_FRONTEND_PHASES = {"LEXER": "léxica", "PARSER": "sintáctica"}


CODE_FONT_STYLE = (
    'font-family: "Cascadia Mono", Consolas, "DejaVu Sans Mono", "Courier New", '
    "monospace; font-size: 10pt;"
)


def monospace_font() -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(10)
    return font


def use_code_font(widget: QWidget) -> None:
    """Monospaced text even under the theme stylesheet, which sets a UI font."""
    widget.setFont(monospace_font())
    widget.setStyleSheet(CODE_FONT_STYLE)


def rejection_message(compilation: object | None) -> str:
    """Why no TAC exists for ``compilation`` (``""`` when it was accepted)."""
    if compilation is None:
        return "Compile un programa para ver su código intermedio."
    if compilation.accepted:
        return ""
    stage = STAGE_NAMES.get(compilation.failed_stage, compilation.failed_stage)
    return (
        f"No se generó TAC: la compilación se detuvo en la fase {stage}. "
        "Revise la pestaña Resumen."
    )


# ----------------------------------------------------------------- diagnostics


@dataclass(frozen=True, slots=True)
class DiagnosticRow:
    """One diagnostic of any phase, flattened for presentation."""

    phase: str
    severity: str
    kind: str
    line: int | None
    column: int | None
    message: str


def collect_diagnostics(compilation: object | None) -> tuple[DiagnosticRow, ...]:
    """Every diagnostic of a compilation in phase order: frontend, semantics, IR."""
    if compilation is None:
        return ()
    rows = [
        DiagnosticRow(
            _FRONTEND_PHASES.get(diagnostic.stage, diagnostic.stage.lower()),
            diagnostic.severity.upper(),
            diagnostic.stage.lower(),
            diagnostic.line,
            diagnostic.column,
            diagnostic.message,
        )
        for diagnostic in compilation.syntax_result.diagnostics
    ]
    if compilation.semantic_result is not None:
        rows += [
            DiagnosticRow(
                "semántica",
                diagnostic.severity.value.upper(),
                diagnostic.category.value,
                diagnostic.location.line,
                diagnostic.location.column,
                diagnostic.message,
            )
            for diagnostic in compilation.semantic_result.diagnostics
        ]
    if compilation.intermediate_result is not None:
        rows += [
            DiagnosticRow(
                "generación",
                "ERROR",
                diagnostic.code,
                diagnostic.location.line if diagnostic.location is not None else None,
                diagnostic.location.column if diagnostic.location is not None else None,
                diagnostic.message,
            )
            for diagnostic in compilation.intermediate_result.diagnostics
        ]
    return tuple(rows)


def _read_only_table(headers: list[str], stretch_column: int) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    table.horizontalHeader().setSectionResizeMode(
        stretch_column, QHeaderView.ResizeMode.Stretch
    )
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.verticalHeader().setVisible(False)
    return table


def _cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "sí" if value else "no"
    return str(value)


class DiagnosticsTable(QTableWidget):
    """Diagnostics of every phase with type (phase + kind) and location."""

    HEADERS = ["Fase", "Severidad", "Tipo", "Línea", "Col", "Mensaje"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)

    def set_compilation(self, compilation: object | None) -> None:
        rows = collect_diagnostics(compilation)
        self.setRowCount(len(rows))
        for index, row in enumerate(rows):
            cells = [row.phase, row.severity, row.kind, _cell(row.line), _cell(row.column),
                     row.message]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == 1:
                    item.setForeground(
                        Qt.GlobalColor.red if row.severity == "ERROR"
                        else Qt.GlobalColor.darkYellow
                    )
                self.setItem(index, column, item)


# ------------------------------------------------------------------------ TAC


class TacView(QWidget):
    """Read-only TAC with search, copy and optional export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        bar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar en el TAC (Enter = siguiente)")
        self._search.returnPressed.connect(self.find_next)
        bar.addWidget(self._search, 1)
        self._find_btn = QPushButton("Buscar")
        self._find_btn.clicked.connect(self.find_next)
        bar.addWidget(self._find_btn)
        self._copy_btn = QPushButton("Copiar")
        self._copy_btn.clicked.connect(self.copy_to_clipboard)
        bar.addWidget(self._copy_btn)
        self._export_btn = QPushButton("Exportar .tac…")
        bar.addWidget(self._export_btn)
        layout.addLayout(bar)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        use_code_font(self._text)
        layout.addWidget(self._text, 1)

        self.set_compilation(None)

    @property
    def export_button(self) -> QPushButton:
        return self._export_btn

    def tac_text(self) -> str:
        return self._text.toPlainText()

    def status_text(self) -> str:
        return self._status.text()

    def has_tac(self) -> bool:
        return bool(self._text.toPlainText())

    def show_pending(self) -> None:
        """Clear the previous output while a new compilation runs (IDE-03)."""
        self._text.clear()
        self._status.setText("Compilando…")
        self._set_actions_enabled(False)

    def set_compilation(self, compilation: object | None) -> None:
        if compilation is not None and compilation.accepted:
            stats = compilation.intermediate_result.statistics
            self._text.setPlainText(tac_document(compilation.tac))
            self._status.setText(
                f"TAC verificado — {stats['instructions']} instrucciones, "
                f"{stats['procedures']} procedimientos, "
                f"{stats['temporaries_created']} temporales creados, "
                f"pico de {stats['temporary_peak']} temporales vivos."
            )
            self._set_actions_enabled(True)
            return
        self._text.clear()
        self._status.setText(rejection_message(compilation))
        self._set_actions_enabled(False)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for widget in (self._copy_btn, self._export_btn, self._find_btn, self._search):
            widget.setEnabled(enabled)

    def find_next(self) -> bool:
        """Select the next match, wrapping to the start once."""
        needle = self._search.text()
        if not needle:
            return False
        if self._text.find(needle):
            return True
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self._text.setTextCursor(cursor)
        return self._text.find(needle, QTextDocument.FindFlag(0))

    def set_search_text(self, text: str) -> None:
        self._search.setText(text)

    def selected_text(self) -> str:
        return self._text.textCursor().selectedText()

    def copy_to_clipboard(self) -> None:
        if self.has_tac():
            QApplication.clipboard().setText(self.tac_text())

    def export(self, path: str | Path) -> Path:
        """Write the shown TAC to ``path`` in UTF-8 with LF line endings."""
        if not self.has_tac():
            raise ValueError("no hay TAC aceptado para exportar")
        target = Path(path)
        target.write_text(self.tac_text(), encoding="utf-8", newline="\n")
        return target


# ------------------------------------------------------- extended symbol table


SYMBOL_COLUMNS = (
    ("name", "Nombre"),
    ("kind", "Clase"),
    ("type", "Tipo"),
    ("storage", "Almacenamiento"),
    ("offset", "Offset"),
    ("size", "Tamaño"),
    ("alignment", "Alineación"),
    ("label", "Etiqueta"),
    ("level", "Nivel"),
    ("frame", "Frame"),
    ("captured", "Capturado"),
    ("env_offset", "Offset env"),
)


class LayoutPanel(QWidget):
    """Extended symbol table on top, activation records (frames) below."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._symbols = _read_only_table([title for _, title in SYMBOL_COLUMNS], 2)
        self._symbols.setSortingEnabled(False)
        splitter.addWidget(self._symbols)

        self._frames = QTreeWidget()
        self._frames.setColumnCount(5)
        self._frames.setHeaderLabels(["Registro / slot", "Tipo de slot", "Offset", "Tamaño",
                                      "Detalle"])
        header = self._frames.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for column, width in enumerate((250, 95, 60, 70)):
            self._frames.setColumnWidth(column, width)
        splitter.addWidget(self._frames)
        splitter.setSizes([300, 360])
        layout.addWidget(splitter, 1)

        self.set_compilation(None)

    @property
    def symbol_table(self) -> QTableWidget:
        return self._symbols

    @property
    def frame_tree(self) -> QTreeWidget:
        return self._frames

    def show_pending(self) -> None:
        self._clear()
        self._status.setText("Compilando…")

    def _clear(self) -> None:
        self._symbols.setRowCount(0)
        self._frames.clear()

    def set_compilation(self, compilation: object | None) -> None:
        self._clear()
        if compilation is None or not compilation.accepted:
            message = rejection_message(compilation)
            self._status.setText(message.replace("TAC", "tabla extendida") if message else "")
            return
        intermediate = compilation.intermediate_result
        rows = intermediate.symbol_layouts.rows()
        frames = intermediate.activation_records
        self._status.setText(
            f"{len(rows)} símbolos con almacenamiento; {len(frames)} registros de "
            f"activación (global + {len(frames) - 1} procedimientos); área estática de "
            f"{intermediate.symbol_layouts.static_size} bytes."
        )
        self._symbols.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, (key, _) in enumerate(SYMBOL_COLUMNS):
                self._symbols.setItem(index, column, QTableWidgetItem(_cell(row[key])))
        for frame in frames:
            self._frames.addTopLevelItem(_frame_item(frame))
        if self._frames.topLevelItemCount():
            self._frames.topLevelItem(0).setExpanded(True)


def _frame_item(frame: object) -> QTreeWidgetItem:
    detail = f"nivel léxico {frame.level}"
    if frame.needs_env:
        detail += "; recibe env (enlace de acceso)"
    item = QTreeWidgetItem(
        [f"{frame.label}  ({frame.name})", "registro", "", f"{frame.size}", detail]
    )
    groups = (
        ("Encabezado", frame.header),
        ("Parámetros ocultos", frame.hidden_parameters),
        ("Parámetros", frame.parameters),
        ("Locales", frame.locals),
        ("Temporales", frame.temporaries),
    )
    for title, slots in groups:
        group = QTreeWidgetItem([title, "", "", str(sum(s.size for s in slots)),
                                 f"{len(slots)} slot(s)"])
        for slot in slots:
            group.addChild(
                QTreeWidgetItem(
                    [
                        slot.name,
                        slot.kind.value,
                        str(slot.offset),
                        str(slot.size),
                        str(slot.type) if slot.type is not None else "",
                    ]
                )
            )
        item.addChild(group)
        group.setExpanded(True)
    if frame.captures:
        captures = QTreeWidgetItem(["Capturas", "", "", "", f"{len(frame.captures)}"])
        for capture in frame.captures:
            captures.addChild(
                QTreeWidgetItem(
                    [
                        capture.symbol.name,
                        "captura",
                        str(capture.env_offset),
                        "",
                        f"dueño {capture.owner_frame}, distancia {capture.depth}",
                    ]
                )
            )
        item.addChild(captures)
        captures.setExpanded(True)
    if frame.environment is not None:
        environment = frame.environment
        env_item = QTreeWidgetItem(
            ["Entorno (closure)", "env", "", str(environment.size),
             f"enlace de acceso en offset {environment.parent_offset}"]
        )
        for slot in environment.slots:
            env_item.addChild(
                QTreeWidgetItem([slot.symbol.name, "env", str(slot.offset), str(slot.size),
                                 str(slot.symbol.type)])
            )
        item.addChild(env_item)
        env_item.setExpanded(True)
    return item


__all__ = [
    "DiagnosticRow",
    "DiagnosticsTable",
    "LayoutPanel",
    "TacView",
    "collect_diagnostics",
    "rejection_message",
]
