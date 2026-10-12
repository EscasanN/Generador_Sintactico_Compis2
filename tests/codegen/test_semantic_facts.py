"""The real SemanticFacts adapter satisfies Daniel's protocol (EXP-05, SYM-05, SYM-06)."""

import pytest

from src.codegen.builder import IRBuilder
from src.codegen.contracts import Address, LexicalAccess
from src.codegen.expression_lowering import ExpressionLowerer
from src.codegen.ir import OpCode, OperandKind
from src.codegen.semantic_facts import MissingFactError
from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.symbol_table import ScopeKind, SymbolKind
from src.semantic.types import FLOAT, INTEGER, ClassType


def declaration(tree, walk, name):
    return next(
        node
        for node in walk(tree)
        if node.rule_name in {"variableDeclaration", "constantDeclaration"}
        and any(child.text == name for child in node.children)
    )


def initializer(node):
    """The ``expression`` node of ``let name = <expression>;``."""
    for child in node.children:
        if child.rule_name == "initializer":
            return next(c for c in child.children if c.rule_name == "expression")
        if child.rule_name == "expression":
            return child
    raise AssertionError("declaration without initializer")


# -- queries ------------------------------------------------------------------------


def test_value_symbol_and_scope_come_from_the_retained_nodes(compile_facts, find_references):
    run, facts = compile_facts("let a: integer = 1;\nlet b: integer = a;\n")
    (reference,) = find_references(run.syntax_result.tree, "a")

    assert facts.value_for(reference).type == INTEGER
    symbol = facts.symbol_for(reference)
    assert symbol.name == "a" and symbol.kind is SymbolKind.VARIABLE
    assert facts.value_for(reference).symbol is symbol
    assert facts.scope_for(reference).kind is ScopeKind.GLOBAL


def test_missing_facts_raise_lookup_errors_instead_of_inventing_values(compile_facts):
    from src.antlr_mode.parse_tree import ParseTreeNode

    _, facts = compile_facts("let a: integer = 1;\n")
    stranger = ParseTreeNode("x", rule_name="expression", line=3, column=4)
    with pytest.raises(MissingFactError, match="expression@3:4"):
        facts.value_for(stranger)
    with pytest.raises(LookupError):
        facts.scope_for(stranger)
    assert facts.symbol_for(stranger) is None


def test_address_retains_symbol_identity_and_reflects_storage(compile_facts, find_references):
    source = (
        "let g: integer = 1;\n"
        "function f(p: integer): integer { let l: integer = p; return l; }\n"
    )
    run, facts = compile_facts(source)
    table = run.semantic_result.symbol_table
    g = table.global_scope.resolve_local("g")
    address = facts.address_for(g)
    assert isinstance(address, Address) and address.symbol is g
    assert (address.storage, address.offset, address.scope) == ("static", 0, None)

    (p_ref,) = find_references(run.syntax_result.tree, "p")
    p = facts.symbol_for(p_ref)
    local = facts.address_for(p)
    assert (local.storage, local.offset, local.scope) == ("parameter", 32, "fn_f")
    assert facts.address_for(p) == local

    from src.semantic.symbol_table import Symbol

    with pytest.raises(LookupError):
        facts.address_for(Symbol("g", SymbolKind.VARIABLE, INTEGER, True, g.location))


def test_member_offset_includes_inherited_fields(compile_facts):
    source = """
    class Base { let a: integer; let b: float; }
    class Hija : Base { let c: integer; }
    """
    _, facts = compile_facts(source)
    base, hija = ClassType("Base"), ClassType("Hija", ClassType("Base"))
    assert facts.member_offset(base, "b") == 8
    assert facts.member_offset(hija, "a") == 0
    assert facts.member_offset(hija, "c") == 16
    with pytest.raises(LookupError):
        facts.member_offset(hija, "nada")
    with pytest.raises(LookupError):
        facts.member_offset(INTEGER, "a")
    with pytest.raises(LookupError):
        facts.member_offset(ClassType("Desconocida"), "a")


# -- lexical access -------------------------------------------------------------------


def test_access_kinds_global_local_field_method_and_code(compile_facts, find_references, walk_tree):
    source = """
    let g: integer = 1;
    class C {
      let campo: integer;
      function leer(): integer { return this.campo; }
    }
    function f(p: integer): integer { let l: integer = p + g; return l; }
    """
    run, facts = compile_facts(source)
    tree = run.syntax_result.tree

    (g_in_f,) = find_references(tree, "g")
    assert facts.lexical_access(g_in_f, facts.symbol_for(g_in_f)) == LexicalAccess("global", 0, 0)

    (p_use,) = find_references(tree, "p")
    p_access = facts.lexical_access(p_use, facts.symbol_for(p_use))
    assert p_access == LexicalAccess("local", 0, 32)

    (l_use,) = find_references(tree, "l")
    assert facts.lexical_access(l_use, facts.symbol_for(l_use)).kind == "local"

    access = next(n for n in walk_tree(tree) if n.alternative == "PropertyAccessExpr")
    field = facts.symbol_for(access)
    assert field.kind is SymbolKind.FIELD
    assert facts.lexical_access(access, field) == LexicalAccess("field", 0, 0)

    table = run.semantic_result.symbol_table.global_scope
    leer = next(s for s in facts.layouts.classes["C"].symbol.metadata["members"].values() if s.kind is SymbolKind.METHOD)
    assert facts.lexical_access(access, leer).kind == "method"
    assert facts.lexical_access(access, table.resolve_local("f")).kind == "global"
    assert facts.lexical_access(access, table.resolve_local("C")).kind == "global"


def test_capture_depths_one_and_two_levels(compile_facts, find_references):
    source = """
    function a(): integer {
      let x: integer = 1;
      function b(): integer {
        let y: integer = 2;
        function c(): integer { return x + y; }
        return c();
      }
      return b();
    }
    """
    run, facts = compile_facts(source)
    tree = run.syntax_result.tree
    x_use = find_references(tree, "x")[-1]
    y_use = find_references(tree, "y")[-1]

    assert facts.lexical_access(x_use, facts.symbol_for(x_use)) == LexicalAccess("captured", 1, 0)
    assert facts.lexical_access(y_use, facts.symbol_for(y_use)) == LexicalAccess("captured", 0, 0)


def test_the_declaring_function_still_sees_its_captured_variable_as_local(
    compile_facts, find_references
):
    source = """
    function f(): integer {
      let x: integer = 1;
      function g(): integer { return x; }
      return g() + x;
    }
    """
    run, facts = compile_facts(source)
    inside_g, inside_f = find_references(run.syntax_result.tree, "x")
    assert facts.lexical_access(inside_g, facts.symbol_for(inside_g)).kind == "captured"
    assert facts.lexical_access(inside_f, facts.symbol_for(inside_f)).kind == "local"


def test_recursion_is_a_label_reference_not_a_capture(compile_facts, find_references):
    source = """
    function fact(n: integer): integer {
      if (n <= 1) { return 1; }
      return n * fact(n - 1);
    }
    """
    run, facts = compile_facts(source)
    (call,) = find_references(run.syntax_result.tree, "fact")
    assert facts.lexical_access(call, facts.symbol_for(call)).kind == "global"
    assert facts.label_for(facts.symbol_for(call)) == "fn_fact"


def test_nested_function_reference_is_local_to_its_creator(compile_facts, find_references):
    source = """
    function f(): integer {
      function g(): integer { return 1; }
      return g();
    }
    """
    run, facts = compile_facts(source)
    (call,) = find_references(run.syntax_result.tree, "g")
    assert facts.lexical_access(call, facts.symbol_for(call)).kind == "local"
    assert facts.label_for(facts.symbol_for(call)) == "fn_f.g"


def test_activation_for_a_node_is_its_enclosing_function_or_the_global_frame(
    compile_facts, find_references
):
    source = "let g: integer = 1;\nfunction f(): integer { return g; }\nlet h: integer = g;\n"
    run, facts = compile_facts(source)
    inside, outside = find_references(run.syntax_result.tree, "g")
    assert facts.activation_for(inside).label == "fn_f"
    assert facts.activation_for(outside) is facts.layouts.global_frame
    assert facts.declaring_scope(facts.symbol_for(inside)).kind is ScopeKind.GLOBAL


# -- the protocol really drives Daniel's lowering -----------------------------------


def test_expression_lowerer_runs_against_real_facts(compile_facts, walk_tree):
    run, facts = compile_facts(
        "let a: integer = 1;\nlet b: integer = 2;\nlet c: integer = a + b * 2;\n"
    )
    builder = IRBuilder()
    value = ExpressionLowerer(builder, facts).lower(
        initializer(declaration(run.syntax_result.tree, walk_tree, "c"))
    )
    code = builder.build().global_code
    arithmetic = [i for i in code if i.opcode in (OpCode.MUL, OpCode.ADD)]
    assert [i.opcode for i in arithmetic] == [OpCode.MUL, OpCode.ADD]
    copied = {
        i.arg1.value.symbol.name: i.arg1.value
        for i in code
        if i.opcode is OpCode.COPY and i.arg1.kind is OperandKind.SYMBOL
    }
    assert set(copied) == {"a", "b"}
    assert copied["b"] == facts.address_for(copied["b"].symbol)
    assert value.type == INTEGER


def test_assignment_lowering_writes_the_shadowing_symbol_not_the_outer_one(
    compile_facts, walk_tree
):
    source = """
    let n: integer = 1;
    { let n: integer = 2; let m: integer = (n = 5); }
    """
    run, facts = compile_facts(source)
    tree = run.syntax_result.tree
    assignment = next(
        n for n in walk_tree(tree) if n.alternative == "ParenPrimary"
    )
    expression = next(c for c in assignment.children if c.rule_name == "expression")
    builder = IRBuilder()
    ExpressionLowerer(builder, facts).lower(expression)
    (copy,) = [i for i in builder.build().global_code if i.opcode is OpCode.COPY]
    target = copy.result.value
    inner = next(
        s for scope in run.semantic_result.symbol_table.iter_scopes()
        if scope.kind is ScopeKind.BLOCK for s in scope.symbols if s.name == "n"
    )
    assert target.symbol is inner
    assert target.symbol is not run.semantic_result.symbol_table.global_scope.resolve_local("n")
    assert target.offset == facts.layouts.symbols.layout_for(inner).offset


def test_same_declaration_feeds_layout_codegen_and_final_view(compile_facts):
    """SYM-06: one Symbol identity from semantics to the extended table."""
    run, facts = compile_facts("let a: integer = 1;\nconst b: float = 2.5;\n")
    scope = run.semantic_result.symbol_table.global_scope
    for symbol in scope.symbols:
        layout = facts.layouts.symbols.layout_for(symbol)
        assert layout.symbol is symbol
        assert facts.address_for(symbol).symbol is symbol
    assert {row["name"] for row in facts.layouts.symbols.rows()} == {"a", "b"}
    assert facts.layouts.symbols.layout_for(scope.resolve_local("b")).size == 8


def test_facts_can_be_rebuilt_from_a_fresh_analysis_with_identical_layouts():
    from pathlib import Path

    from src.codegen.semantic_facts import SemanticFactsIndex

    root = Path(__file__).resolve().parents[2]
    source = (root / "tests" / "cps" / "validos" / "FUN-04-closure.cps").read_text(encoding="utf8")

    def rows():
        run = analyze_semantics_with_g4(
            root / "src/compiscript/grammar/Compiscript.g4",
            source,
            root / "semantic_profiles/compiscript.semantic.json",
            "program",
        )
        return SemanticFactsIndex.from_result(run.semantic_result, run.syntax_result.tree).layouts.symbols.rows()

    assert rows() == rows()
