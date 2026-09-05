"""End-to-end Compiscript coverage for block 4 (Nelson).

Every test below drives the *real* official grammar
(``src/compiscript/grammar/Compiscript.g4``) and the *real* semantic profile
(``semantic_profiles/compiscript.semantic.json``) through
``analyze_semantics_with_extensions`` -- the same entrypoint the IDE uses --
never a hand-built manual tree. Each mandatory row of
``docs/phase3/MATRIZ_CUMPLIMIENTO.md`` gets one accepted (positive) case and
one rejected (negative) case, named after its identifier so the evidence is
easy to locate. Test names double as the traceability index.
"""

from pathlib import Path

import pytest

from src.gui.semantic_bridge import analyze_semantics_with_extensions

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"


def compile_source(source: str):
    """Run the full syntax+semantics pipeline used by the IDE."""
    return analyze_semantics_with_extensions(
        GRAMMAR, source, PROFILE, "program", "tests/end_to_end.cps"
    )


def assert_accepted(source: str):
    result = compile_source(source)
    assert result.syntax_result.accepted, result.syntax_result.diagnostics
    assert result.semantic_result is not None
    assert result.accepted, result.semantic_result.diagnostics
    return result


def assert_rejected(source: str, expected_category: str | None = None):
    result = compile_source(source)
    if not result.syntax_result.accepted:
        return result
    assert result.semantic_result is not None
    assert not result.accepted
    assert result.semantic_result.diagnostics
    if expected_category is not None:
        assert any(
            d.category.value == expected_category
            for d in result.semantic_result.diagnostics
        )
    return result


# ---------------------------------------------------------------------------
# TYP -- Sistema de tipos
# ---------------------------------------------------------------------------


def test_typ_01_success_arithmetic_accepts_integers():
    assert_accepted("let x: integer = 1 + 2 * 3;")


def test_typ_01_failure_arithmetic_rejects_boolean_operand():
    assert_rejected('let x: integer = true + 1;', "type")


def test_typ_02_success_logic_accepts_booleans():
    assert_accepted("let x: boolean = true && !false;")


def test_typ_02_failure_logic_rejects_non_boolean():
    assert_rejected("let x: boolean = 1 && true;", "type")


def test_typ_03_success_comparison_uses_compatible_types():
    assert_accepted("let x: boolean = 1 < 2;")


def test_typ_03_failure_comparison_uses_incompatible_types():
    assert_rejected('let x: boolean = 1 == "text";', "type")


def test_typ_04_success_assignment_matches_declared_type():
    assert_accepted("let x: integer = 1; x = 2;")


def test_typ_04_failure_assignment_mismatches_declared_type():
    assert_rejected('let x: integer; x = "text";', "type")


def test_typ_05_success_constant_has_compatible_initializer():
    assert_accepted("const c: integer = 5;")


def test_typ_05_failure_constant_without_initializer_is_a_syntax_error():
    # The official grammar requires '=' expression for constantDeclaration,
    # so an uninitialized constant cannot even be parsed -- confirming the
    # rule is already enforced structurally (see REGLAS_Y_DECISIONES.md).
    result = compile_source("const c: integer;")
    assert not result.syntax_result.accepted


def test_typ_06_success_list_has_a_common_element_type():
    assert_accepted("let xs: integer[] = [1, 2, 3];")


def test_typ_06_failure_list_has_incompatible_elements():
    assert_rejected('let xs = [1, "text"];', "array")


# ---------------------------------------------------------------------------
# SCP -- Manejo de ámbito
# ---------------------------------------------------------------------------


def test_scp_01_success_resolves_the_closest_declaration():
    assert_accepted("let x: integer = 1; { let y: integer = x; }")


def test_scp_01_failure_uses_an_undeclared_variable():
    assert_rejected("let y: integer = x;", "scope")


def test_scp_02_success_shadowing_in_a_child_scope_is_allowed():
    assert_accepted("let x: integer = 1; { let x: integer = 2; }")


def test_scp_02_failure_redeclaration_in_the_same_scope_is_rejected():
    assert_rejected("let x: integer = 1; let x: integer = 2;", "scope")


def test_scp_03_success_nested_block_reads_its_ancestor():
    assert_accepted("let x: integer = 1; { { let y: integer = x; } }")


def test_scp_03_failure_name_is_not_visible_once_its_block_closes():
    assert_rejected("{ let x: integer = 1; } let y: integer = x;", "scope")


def test_scp_04_success_function_class_and_block_each_open_an_environment():
    assert_accepted(
        """
        function f(): integer {
          let a: integer = 1;
          return a;
        }
        class C {
          let b: integer;
          function constructor() { this.b = 1; }
        }
        { let c: integer = 1; }
        """
    )


def test_scp_04_failure_block_locals_do_not_leak_into_the_parent_scope():
    assert_rejected(
        """
        function f(): integer {
          if (true) { let inner: integer = 1; }
          return inner;
        }
        """,
        "scope",
    )


# ---------------------------------------------------------------------------
# FUN -- Funciones y procedimientos
# ---------------------------------------------------------------------------


def test_fun_01_success_call_matches_arity_and_types():
    assert_accepted(
        "function add(a: integer, b: integer): integer { return a + b; } "
        "let r: integer = add(1, 2);"
    )


def test_fun_01_failure_call_has_wrong_arity():
    assert_rejected(
        "function add(a: integer, b: integer): integer { return a + b; } "
        "let r: integer = add(1);",
        "function",
    )


def test_fun_02_success_return_matches_declared_type():
    assert_accepted("function f(): integer { return 1; }")


def test_fun_02_failure_return_mismatches_declared_type():
    assert_rejected('function f(): integer { return "text"; }', "function")


def test_fun_03_success_function_resolves_itself_recursively():
    assert_accepted(
        "function fact(n: integer): integer { "
        "if (n <= 1) { return 1; } return n * fact(n - 1); }"
    )


def test_fun_03_failure_recursive_reference_without_a_function_symbol():
    # A plain (non-function) name cannot be called recursively.
    assert_rejected("let fact: integer = 1; let x: integer = fact(1);", "function")


def test_fun_04_success_nested_function_sees_the_enclosing_variable():
    assert_accepted(
        """
        function outer(): integer {
          let base: integer = 10;
          function inner(): integer {
            return base;
          }
          return inner();
        }
        """
    )


def test_fun_04_failure_nested_function_uses_an_out_of_scope_name():
    assert_rejected(
        """
        function outer(): integer {
          function inner(): integer {
            return missing;
          }
          return inner();
        }
        """,
        "scope",
    )


def test_fun_05_success_distinct_function_names_coexist():
    assert_accepted(
        "function f(): integer { return 1; } function g(): integer { return 2; }"
    )


def test_fun_05_failure_duplicate_function_name_in_the_same_scope():
    assert_rejected(
        "function f(): integer { return 1; } function f(): integer { return 2; }",
        "function",
    )


# ---------------------------------------------------------------------------
# CTL -- Control de flujo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "if (true) { print(1); }",
        "while (true) { break; }",
        "do { break; } while (true);",
        "for (let i: integer = 0; true; i = i + 1) { break; }",
        'switch (true) { case true: print(1); }',
    ],
    ids=["if", "while", "do-while", "for", "switch"],
)
def test_ctl_01_success_every_construct_accepts_a_boolean_condition(source):
    assert_accepted(source)


@pytest.mark.parametrize(
    "source",
    [
        "if (1) { print(1); }",
        "while (1) { break; }",
        "do { break; } while (1);",
        "for (let i: integer = 0; 1; i = i + 1) { break; }",
        "switch (1) { case true: print(1); }",
    ],
    ids=["if", "while", "do-while", "for", "switch"],
)
def test_ctl_01_failure_every_construct_rejects_a_non_boolean_condition(source):
    assert_rejected(source, "control_flow")


def test_ctl_02_success_break_and_continue_are_inside_a_loop():
    assert_accepted("while (true) { break; continue; }")


def test_ctl_02_failure_break_and_continue_are_outside_any_loop():
    assert_rejected("break;", "control_flow")
    assert_rejected("continue;", "control_flow")


def test_ctl_03_success_return_is_inside_a_function():
    assert_accepted("function f(): integer { return 1; }")


def test_ctl_03_failure_return_in_the_global_scope():
    assert_rejected("return 1;", "control_flow")


def test_ctl_03_failure_return_inside_a_bare_block_without_a_function():
    assert_rejected("{ return 1; }", "control_flow")


# ---------------------------------------------------------------------------
# CLS -- Clases y objetos
# ---------------------------------------------------------------------------


CLASS_WITH_MEMBERS = """
class Point {
  let x: integer;
  let y: integer;
  function constructor(x: integer, y: integer) {
    this.x = x;
    this.y = y;
  }
  function sum(): integer {
    return this.x + this.y;
  }
}
"""


def test_cls_01_success_member_access_reaches_a_declared_field_and_method():
    assert_accepted(
        CLASS_WITH_MEMBERS
        + "let p = new Point(1, 2); let s: integer = p.sum(); let px: integer = p.x;"
    )


def test_cls_01_failure_member_access_reaches_an_undeclared_member():
    assert_rejected(CLASS_WITH_MEMBERS + "let p = new Point(1, 2); let z = p.missing;", "class")


def test_cls_02_success_constructor_is_invoked_with_matching_arguments():
    assert_accepted(CLASS_WITH_MEMBERS + "let p = new Point(1, 2);")


def test_cls_02_failure_constructor_has_no_matching_member():
    assert_rejected("class Empty { } let e = new Empty();", "class")


def test_cls_02_failure_constructor_call_has_wrong_arity():
    assert_rejected(CLASS_WITH_MEMBERS + "let p = new Point(1);", "function")


def test_cls_03_success_this_is_used_inside_a_method():
    assert_accepted(CLASS_WITH_MEMBERS)


def test_cls_03_failure_this_is_used_outside_any_class():
    assert_rejected("let x = this;", "class")


# ---------------------------------------------------------------------------
# LST -- Listas
# ---------------------------------------------------------------------------


def test_lst_01_success_list_elements_share_a_valid_type():
    assert_accepted("let xs: integer[] = [1, 2, 3];")


def test_lst_01_failure_list_elements_are_incompatible():
    assert_rejected('let xs = [true, "text"];', "array")


def test_lst_02_success_list_index_is_an_integer():
    assert_accepted("let xs: integer[] = [1, 2, 3]; let first: integer = xs[0];")


@pytest.mark.parametrize("bad_index", ['"x"', "true", "1.5"])
def test_lst_02_failure_list_index_is_not_an_integer(bad_index):
    assert_rejected(f"let xs: integer[] = [1, 2, 3]; let v = xs[{bad_index}];", "array")


# ---------------------------------------------------------------------------
# GEN -- Reglas generales
# ---------------------------------------------------------------------------


def test_gen_01_success_no_instruction_follows_a_definitive_transfer():
    result = assert_accepted("function f(): integer { return 1; }")
    assert not any(
        "unreachable" in d.message for d in result.semantic_result.diagnostics
    )


def test_gen_01_failure_instruction_after_return_is_flagged():
    result = compile_source(
        "function f(): integer { return 1; let x: integer = 2; }"
    )
    assert result.accepted  # a warning does not reject the program
    assert any(
        "unreachable" in d.message for d in result.semantic_result.diagnostics
    )


def test_gen_01_failure_instruction_after_break_is_flagged():
    result = compile_source("while (true) { break; print(1); }")
    assert result.accepted
    assert any(
        "unreachable" in d.message for d in result.semantic_result.diagnostics
    )


def test_gen_02_success_expression_operands_make_semantic_sense():
    assert_accepted("let x: integer = 2 * 3;")


def test_gen_02_failure_multiplying_a_function_value_is_rejected():
    assert_rejected(
        "function f(): integer { return 1; } let x: integer = f * 2;",
        "type",
    )


def test_gen_03_success_distinct_names_in_the_same_scope():
    assert_accepted("let a: integer = 1; let b: integer = 2;")


def test_gen_03_failure_duplicate_variable_in_the_same_scope():
    assert_rejected("let a: integer = 1; let a: integer = 2;", "scope")


def test_gen_03_failure_duplicate_parameter_name_in_a_signature():
    assert_rejected(
        "function f(a: integer, a: integer): integer { return a; }", "function"
    )


# ---------------------------------------------------------------------------
# ANT -- Integración ANTLR (repetido desde el bloque 4 con la gramática final)
# ---------------------------------------------------------------------------


def test_ant_06_official_grammar_and_profile_accept_a_complete_program():
    assert_accepted(
        """
        class Counter {
          let n: integer;
          function constructor() { this.n = 0; }
          function inc(): integer {
            this.n = this.n + 1;
            return this.n;
          }
        }
        function sumTo(n: integer): integer {
          let total: integer = 0;
          for (let i: integer = 1; i <= n; i = i + 1) {
            total = total + i;
          }
          return total;
        }
        let c = new Counter();
        print(c.inc());
        let xs: integer[] = [1, 2, 3];
        let s: integer = sumTo(xs[2]);
        """
    )


def test_ant_06_official_grammar_rejects_a_program_with_mixed_errors():
    result = compile_source(
        """
        let x: integer = 1;
        let x: integer = 2;
        function f(): integer {
          return "text";
        }
        if (1) { print(x); }
        """
    )
    assert not result.accepted
    categories = {d.category.value for d in result.semantic_result.diagnostics}
    assert "scope" in categories
    assert "function" in categories
    assert "control_flow" in categories
