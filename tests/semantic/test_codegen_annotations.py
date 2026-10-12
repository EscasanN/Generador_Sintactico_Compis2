"""Per-node semantic annotations consumed by the code generator (EXP-05, SYM-06)."""

from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

import pytest

from src.antlr_mode.parse_tree import ParseTreeNode
from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.evaluator import SemanticEvaluator
from src.semantic.profile import ActionInvocation, ChildSelector, RuleBinding, SemanticProfile
from src.semantic.results import SemanticAnalysisResult, SemanticAnnotations
from src.semantic.symbol_table import ScopeKind, SymbolKind, SymbolTable
from src.semantic.types import INTEGER, STRING

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"
SHADOWING = (REPO_ROOT / "tests" / "cps" / "validos" / "SCP-02-shadowing.cps").read_text(
    encoding="utf8"
)


@lru_cache(maxsize=None)
def analyze(source: str):
    run = analyze_semantics_with_g4(GRAMMAR, source, PROFILE, "program")
    assert run.accepted, run.semantic_result and run.semantic_result.diagnostics
    return run


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def identifier_references(root, name):
    return [
        node
        for node in walk(root)
        if node.alternative == "IdentifierExpr"
        and any(child.text == name for child in node.children)
    ]


def test_annotation_maps_are_read_only():
    annotations = analyze(SHADOWING).semantic_result.annotations
    for mapping in (
        annotations.values_by_node,
        annotations.symbols_by_node,
        annotations.scopes_by_node,
    ):
        assert isinstance(mapping, MappingProxyType)
        with pytest.raises(TypeError):
            mapping[0] = None
    assert isinstance(annotations.anchors, tuple)


def test_result_built_without_annotations_keeps_working():
    result = SemanticAnalysisResult((), SymbolTable())
    assert result.accepted
    assert result.annotations == SemanticAnnotations()
    assert result.annotations.value_for(object()) is None
    assert result.annotations.symbol_for(object()) is None
    assert result.annotations.scope_for(object()) is None


def test_shadowed_identifiers_resolve_to_different_symbols_and_scopes():
    run = analyze(SHADOWING)
    annotations = run.semantic_result.annotations
    inner, outer = identifier_references(run.syntax_result.tree, "nombre")

    inner_symbol = annotations.symbol_for(inner)
    outer_symbol = annotations.symbol_for(outer)
    assert inner_symbol is not outer_symbol
    assert inner_symbol.location.line == 4
    assert outer_symbol.location.line == 2
    assert annotations.scope_for(inner).kind is ScopeKind.BLOCK
    assert annotations.scope_for(outer).kind is ScopeKind.GLOBAL
    assert annotations.scope_for(inner).resolve_local("nombre") is inner_symbol
    assert annotations.value_for(inner).type == STRING
    assert annotations.value_for(inner).symbol is inner_symbol


def test_function_class_and_block_nodes_report_their_own_scopes():
    source = """
    class Caja { let valor: integer; function leer(): integer { return this.valor; } }
    function doble(n: integer): integer { { let m: integer = n; } return n * 2; }
    """
    run = analyze(source)
    annotations = run.semantic_result.annotations
    by_rule = {}
    for node in walk(run.syntax_result.tree):
        scope = annotations.scope_for(node)
        if scope is not None and node.rule_name in {"classDeclaration", "functionDeclaration", "block"}:
            by_rule.setdefault(node.rule_name, []).append(scope)

    assert {s.kind for s in by_rule["classDeclaration"]} == {ScopeKind.CLASS}
    assert by_rule["classDeclaration"][0].name == "Caja"
    assert ScopeKind.FUNCTION in {s.kind for s in by_rule["functionDeclaration"]}
    assert any(s.kind is ScopeKind.BLOCK for s in by_rule["block"])
    doble = next(s for s in by_rule["functionDeclaration"] if s.name == "doble")
    assert doble.resolve_local("n").kind is SymbolKind.PARAMETER


def test_every_visited_node_has_a_scope_and_a_retained_anchor():
    run = analyze(SHADOWING)
    annotations = run.semantic_result.annotations
    nodes = list(walk(run.syntax_result.tree))
    assert all(annotations.scope_for(node) is not None for node in nodes)
    anchor_ids = {id(anchor) for anchor in annotations.anchors}
    assert {id(node) for node in nodes} <= anchor_ids


def test_assignment_statement_exposes_the_target_symbol():
    run = analyze("let x: integer = 1;\n{ let x: integer = 2; x = 3; }\nx = 4;\n")
    annotations = run.semantic_result.annotations
    assignments = [n for n in walk(run.syntax_result.tree) if n.alternative == "SimpleAssignment"]
    inner, outer = (annotations.symbol_for(node) for node in assignments)
    assert inner is not outer
    assert inner.location.line == 2 and outer.location.line == 1


def test_declaration_nodes_expose_declared_symbols_and_values():
    run = analyze("const k: integer = 5;\n")
    annotations = run.semantic_result.annotations
    declaration = next(n for n in walk(run.syntax_result.tree) if n.rule_name == "constantDeclaration")
    symbol = annotations.symbol_for(declaration)
    assert symbol.name == "k" and symbol.kind is SymbolKind.CONSTANT
    assert annotations.value_for(declaration).type == INTEGER


def _manual_profile():
    literal = RuleBinding(
        "number",
        (ActionInvocation("expression.literal", {"kind": "integer", "text": ChildSelector("text")}),),
    )
    declaration = RuleBinding(
        "declaration",
        (
            ActionInvocation(
                "declare.variable",
                {"name": "v", "type_": "integer", "initializer": ChildSelector("child", index=0)},
            ),
        ),
    )
    return SemanticProfile("manual", (literal, declaration))


def _manual_node(rule, text=None, children=()):
    return ParseTreeNode(rule, list(children), rule_name=rule, text=text, line=1, column=1)


def test_manual_evaluator_produces_the_same_annotation_shape():
    number = _manual_node("number", "7")
    declaration = _manual_node("declaration", children=(number,))
    root = _manual_node("root", children=(declaration,))
    result = SemanticEvaluator().analyze(root, _manual_profile())

    annotations = result.annotations
    assert annotations.value_for(number).constant_value == 7
    assert annotations.value_for(declaration).symbol is annotations.symbol_for(declaration)
    assert annotations.symbol_for(declaration).name == "v"
    assert all(
        annotations.scope_for(node) is result.symbol_table.global_scope
        for node in (root, declaration, number)
    )


def test_evaluator_clears_mutable_node_state_even_when_a_walk_aborts():
    evaluator = SemanticEvaluator()
    bad_profile = SemanticProfile(
        "bad",
        (RuleBinding("number", (ActionInvocation("no.such.action", {}),)),),
    )
    with pytest.raises(Exception):
        evaluator.analyze(_manual_node("number", "1"), bad_profile)
    assert not evaluator.context.node_scopes
    assert not evaluator.context.node_anchors
    assert not evaluator.context.resolved_symbols

    result = evaluator.analyze(_manual_node("number", "1"), _manual_profile())
    assert result.annotations.values_by_node
    assert not evaluator.context.node_scopes
