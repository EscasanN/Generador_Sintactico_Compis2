"""Renderizado Graphviz del árbol sintáctico común de ANTLR."""

from __future__ import annotations

import os

import graphviz

from src.antlr_mode.parse_tree import ParseTreeNode


def render_parse_tree(
    root: ParseTreeNode,
    output_path: str = "output/parse_tree",
    fmt: str = "png",
) -> str:
    """Renderiza un árbol sintáctico y devuelve la ruta del archivo generado."""
    counter = [0]
    dot = graphviz.Digraph(
        name="Parse Tree",
        graph_attr={
            "label": "Parse Tree",
            "labelloc": "t",
            "fontsize": "14",
            "fontname": "Helvetica",
            "rankdir": "TB",
            "nodesep": "0.4",
            "ranksep": "0.6",
        },
        node_attr={"fontname": "Helvetica", "fontsize": "11"},
        edge_attr={"fontname": "Helvetica", "fontsize": "9"},
    )

    def add_node(node: ParseTreeNode) -> str:
        node_id = f"n{counter[0]}"
        counter[0] += 1
        if node.is_leaf:
            dot.node(
                node_id,
                label=node.symbol,
                shape="box",
                style="filled",
                fillcolor="#AED6F1",
            )
        else:
            dot.node(
                node_id,
                label=node.symbol,
                shape="ellipse",
                style="filled",
                fillcolor="#A9DFBF",
            )
        for child in node.children:
            child_id = add_node(child)
            dot.edge(node_id, child_id)
        return node_id

    add_node(root)
    output_directory = os.path.dirname(output_path) or "."
    os.makedirs(output_directory, exist_ok=True)
    dot.render(output_path, format=fmt, cleanup=True)
    return f"{output_path}.{fmt}"


__all__ = ["render_parse_tree"]
