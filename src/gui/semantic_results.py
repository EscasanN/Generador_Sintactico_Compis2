"""Diagnostics and per-environment symbol table panel (IDE-05 / IDE-06).

Reads only the public, frozen shapes already produced by earlier blocks:
``SemanticAnalysisResult`` (Nadissa, ``src/semantic/results.py``) and
``SymbolTable``/``Scope``/``Symbol`` (Nadissa,
``src/semantic/symbol_table.py``). It does not alter either module.
"""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.semantic.diagnostics import Diagnostic, DiagnosticSeverity
from src.semantic.results import SemanticAnalysisResult
from src.semantic.symbol_table import Scope, SymbolTable


def _severity_label(severity: DiagnosticSeverity) -> str:
    return severity.value.upper()


def _populate_diagnostics(table: QTableWidget, diagnostics: Iterable[Diagnostic]) -> None:
    rows = list(diagnostics)
    table.setRowCount(len(rows))
    for row, diagnostic in enumerate(rows):
        location = diagnostic.location
        cells = [
            _severity_label(diagnostic.severity),
            diagnostic.category.value,
            str(location.line),
            str(location.column),
            diagnostic.message,
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if diagnostic.severity is DiagnosticSeverity.ERROR and col == 0:
                item.setForeground(Qt.GlobalColor.red)
            elif col == 0:
                item.setForeground(Qt.GlobalColor.darkYellow)
            table.setItem(row, col, item)


def _scope_label(scope: Scope) -> str:
    name = scope.name or "(sin nombre)"
    return f"{scope.kind.value}: {name}  ({len(scope.symbols)} símbolo(s))"


def _symbol_label(symbol) -> str:
    mutability = "mutable" if symbol.mutable else "inmutable"
    return f"{symbol.name} : {symbol.kind.value} / {symbol.type} ({mutability})"


def _add_scope_item(parent_item: QTreeWidgetItem, scope: Scope) -> None:
    for symbol in scope.symbols:
        leaf = QTreeWidgetItem([_symbol_label(symbol), str(symbol.location.line)])
        parent_item.addChild(leaf)
    for child_scope in scope.children:
        child_item = QTreeWidgetItem([_scope_label(child_scope), ""])
        parent_item.addChild(child_item)
        _add_scope_item(child_item, child_scope)


def _populate_symbol_table(tree: QTreeWidget, symbol_table: SymbolTable | None) -> None:
    tree.clear()
    if symbol_table is None:
        return
    root = symbol_table.global_scope
    root_item = QTreeWidgetItem([_scope_label(root), ""])
    tree.addTopLevelItem(root_item)
    _add_scope_item(root_item, root)
    root_item.setExpanded(True)


class SemanticResultsPanel(QWidget):
    """Diagnostics table on top, per-environment symbol tree below."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self._diagnostics_table = QTableWidget(0, 5)
        self._diagnostics_table.setHorizontalHeaderLabels(
            ["Severity", "Category", "Line", "Col", "Message"]
        )
        self._diagnostics_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self._diagnostics_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._diagnostics_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        splitter.addWidget(self._diagnostics_table)

        self._symbol_tree = QTreeWidget()
        self._symbol_tree.setColumnCount(2)
        self._symbol_tree.setHeaderLabels(["Entorno / símbolo", "Línea"])
        self._symbol_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self._symbol_tree)

        splitter.setSizes([220, 380])
        layout.addWidget(splitter)

    def set_result(self, result: SemanticAnalysisResult | None) -> None:
        """Refresh both panes from a semantic analysis result (or clear)."""
        if result is None:
            self._diagnostics_table.setRowCount(0)
            self._symbol_tree.clear()
            return
        _populate_diagnostics(self._diagnostics_table, result.diagnostics)
        _populate_symbol_table(self._symbol_tree, result.symbol_table)


__all__ = ["SemanticResultsPanel"]
