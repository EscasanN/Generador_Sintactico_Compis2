"""Navigable syntax-tree view for the IDE (IDE-07 / ANT-04).

``src/utils/visualizer.py`` (Dulce's) already renders a Graphviz image of a
``ParseTreeNode``, which is the right choice for a small tree a person wants
to screenshot or print. For a large ``.cps`` program, though, a static image
becomes unreadable and slow to render. This module builds a
:class:`QTreeWidget` instead: expand/collapse per node, a label per row
(rule name or literal token, plus its alternative and text when present),
and the source line/column in a second column. It reads only the public
``ParseTreeNode`` fields (``rule_name``, ``symbol``, ``alternative``,
``token_type``, ``text``, ``line``, ``column``, ``children``) exposed by
Dulce's frozen ``src/parser/parse_tree.py`` and never modifies that module.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem, QWidget


def _label_for(node: Any) -> tuple[str, str]:
    """Return ``(main_label, location_label)`` for one tree node."""
    name = node.rule_name or node.symbol or "?"
    if node.alternative:
        name = f"{name}  [{node.alternative}]"
    if node.token_type is not None:
        text = node.text if node.text is not None else ""
        name = f"{name} = {text!r}"
    location = ""
    if node.line is not None:
        location = f"{node.line}:{node.column}" if node.column is not None else str(node.line)
    return name, location


def _add_children(parent_item: QTreeWidgetItem, node: Any) -> None:
    for child in getattr(node, "children", ()):
        label, location = _label_for(child)
        item = QTreeWidgetItem([label, location])
        parent_item.addChild(item)
        _add_children(item, child)


def build_tree_widget(root: Any, parent: QWidget | None = None) -> QTreeWidget:
    """Build a fully-populated, collapsed-by-default navigable tree widget."""
    widget = QTreeWidget(parent)
    widget.setColumnCount(2)
    widget.setHeaderLabels(["Node", "Location"])
    widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    label, location = _label_for(root)
    root_item = QTreeWidgetItem([label, location])
    widget.addTopLevelItem(root_item)
    _add_children(root_item, root)
    root_item.setExpanded(True)
    return widget


__all__ = ["build_tree_widget"]
