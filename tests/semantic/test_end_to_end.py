"""End-to-end Compiscript coverage for block 4 (Nelson).

Every test below drives the delivery grammar
(``src/compiscript/grammar/Compiscript.g4``) and the *real* semantic profile
(``semantic_profiles/compiscript.semantic.json``) through
``analyze_semantics_with_g4`` -- the same public entrypoint the IDE uses --
never a hand-built manual tree. Each mandatory row of
``docs/phase3/MATRIZ_CUMPLIMIENTO.md`` gets one accepted (positive) case and
one rejected (negative) case, named after its identifier so the evidence is
easy to locate. Test names double as the traceability index.
"""

from pathlib import Path

import pytest

from src.semantic.antlr_adapter import analyze_semantics_with_g4
from src.semantic.evaluator import SemanticEvaluator
from src.semantic.profile import load_profile
from src.semantic.types import INTEGER

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = REPO_ROOT / "src" / "compiscript" / "grammar" / "Compiscript.g4"
PROFILE = REPO_ROOT / "semantic_profiles" / "compiscript.semantic.json"


def test_compiscript_profile_uses_only_builtin_semantic_actions():
    """The GUI profile must run through the public generic adapter unchanged."""
    profile = load_profile(PROFILE)
    registered = set(SemanticEvaluator().registry.names)
    used = {
        action.name
        for binding in profile.bindings
        for action in binding.actions
    }

    assert used <= registered


def compile_source(source: str):
    """Run the full syntax+semantics pipeline used by the IDE."""
    return analyze_semantics_with_g4(
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
    assert result.syntax_result.accepted, (
        "semantic negative fixture must be syntactically valid: "
        f"{result.syntax_result.diagnostics}"
    )
    assert result.semantic_result is not None
    assert not result.accepted
    assert result.semantic_result.diagnostics
    if expected_category is not None:
        assert any(
            d.category.value == expected_category
            for d in result.semantic_result.diagnostics
        )
    return result


def test_semantic_rejection_helper_requires_syntactically_valid_input():
    """Semantic negative evidence must reach the semantic analysis stage."""
    with pytest.raises(AssertionError, match="semantic negative fixture"):
        assert_rejected("let invalid: integer = ;", "type")


# ---------------------------------------------------------------------------
# TYP -- Sistema de tipos
# ---------------------------------------------------------------------------


def test_typ_01_success_arithmetic_accepts_integers():
    assert_accepted("let x: integer = 1 + 2 * 3;")


def test_typ_01_success_arithmetic_accepts_float_literals():
    assert_accepted("let x: float = 1.5 * 2;")


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
    # The delivery grammar requires '=' expression for constantDeclaration,
    # so an uninitialized constant cannot even be parsed -- confirming the
    # rule is already enforced structurally (see REGLAS_Y_DECISIONES.md).
    result = compile_source("const c: integer;")
    assert not result.syntax_result.accepted


def test_typ_06_success_list_has_a_common_element_type():
    assert_accepted("let xs: integer[] = [1, 2, 3];")


def test_typ_06_failure_list_has_incompatible_elements():
    assert_rejected('let xs = [1, "text"];', "array")


def test_typ_06_success_class_field_infers_its_initializer_type():
    result = assert_accepted(
        "class C { let value = 1; function constructor() {} }"
    )
    class_symbol = result.semantic_result.symbol_table.global_scope.resolve_local("C")
    assert class_symbol is not None
    assert class_symbol.metadata["members"]["value"].type == INTEGER


@pytest.mark.parametrize("keyword", ["let", "const"])
def test_typ_06_failure_class_member_initializer_must_match_declared_type(keyword):
    assert_rejected(
        f'class C {{ {keyword} value: integer = "text"; '
        "function constructor() {} }",
        "type",
    )


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


def test_scp_02_failure_duplicate_class_does_not_modify_first_class():
    result = assert_rejected(
        "class C { let original: integer; } "
        "class C { let leaked: integer; }",
        "scope",
    )

    class_symbol = result.semantic_result.symbol_table.global_scope.resolve_local("C")
    assert class_symbol is not None
    assert "original" in class_symbol.metadata["members"]
    assert "leaked" not in class_symbol.metadata["members"]


def test_scp_02_failure_duplicate_function_does_not_reenter_first_function():
    result = assert_rejected(
        "function f(): integer { return 1; } "
        "function f(): integer { return 2; }",
        "function",
    )

    function_scopes = [
        scope
        for scope in result.semantic_result.symbol_table.iter_scopes()
        if scope.kind.value == "function" and scope.name == "f"
    ]
    assert len(function_scopes) == 1


def test_scp_02_failure_duplicate_method_does_not_reenter_first_method():
    result = assert_rejected(
        "class C { "
        "function f(): integer { return 1; } "
        "function f(): integer { return 2; } "
        "}",
        "function",
    )

    method_scopes = [
        scope
        for scope in result.semantic_result.symbol_table.iter_scopes()
        if scope.kind.value == "function" and scope.name == "f"
    ]
    assert len(method_scopes) == 1


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


def test_fun_03_success_global_function_can_be_called_before_declaration():
    """Removing the global signature prepass must make ``later`` unresolved."""
    assert_accepted(
        "let result: integer = later(); "
        "function later(): integer { return 1; }"
    )


def test_fun_03_success_global_functions_support_mutual_recursion():
    """Both global signatures must exist before either body is traversed."""
    assert_accepted(
        "function even(n: integer): boolean { "
        "if (n == 0) { return true; } return odd(n - 1); } "
        "function odd(n: integer): boolean { "
        "if (n == 0) { return false; } return even(n - 1); }"
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


def test_ctl_02_success_foreach_infers_the_array_element_type():
    """Binding the iterator too early leaves it unknown inside the loop body."""
    assert_accepted(
        "let values: integer[] = [1, 2]; "
        "foreach (value in values) { let copy: integer = value; }"
    )


def test_ctl_02_failure_foreach_rejects_a_non_array_iterable():
    assert_rejected("foreach (value in 1) { print(value); }", "array")


def test_ctl_03_success_return_is_inside_a_function():
    assert_accepted("function f(): integer { return 1; }")


def test_ctl_03_failure_return_in_the_global_scope():
    assert_rejected("return 1;", "control_flow")


def test_ctl_03_failure_return_inside_a_bare_block_without_a_function():
    assert_rejected("{ return 1; }", "control_flow")


def test_ctl_04_success_catch_parameter_is_a_scoped_string():
    assert_accepted(
        "try { print(1); } "
        "catch (error) { let message: string = error; }"
    )


def test_ctl_04_failure_catch_parameter_does_not_escape_its_scope():
    assert_rejected(
        "try { print(1); } catch (error) { print(error); } print(error);",
        "scope",
    )


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


def test_cls_01_success_field_declared_after_constructor_is_visible():
    assert_accepted(
        """
        class LateField {
          function constructor(value: integer) { this.value = value; }
          let value: integer;
        }
        let item = new LateField(1);
        """
    )


def test_cls_01_success_method_declared_after_calling_method_is_visible():
    assert_accepted(
        """
        class ForwardCall {
          function first(): integer { return this.second(); }
          function second(): integer { return 2; }
          function constructor() { }
        }
        let item = new ForwardCall();
        let result: integer = item.first();
        """
    )


def test_cls_01_failure_member_access_reaches_an_undeclared_member():
    assert_rejected(CLASS_WITH_MEMBERS + "let p = new Point(1, 2); let z = p.missing;", "class")


def test_cls_02_success_constructor_is_invoked_with_matching_arguments():
    assert_accepted(CLASS_WITH_MEMBERS + "let p = new Point(1, 2);")


def test_cls_02_success_class_without_constructor_uses_implicit_zero_arity():
    assert_accepted("class Empty { } let e = new Empty();")


def test_cls_02_failure_implicit_constructor_rejects_arguments():
    assert_rejected("class Empty { } let e = new Empty(1);", "function")


def test_cls_02_failure_constructor_call_has_wrong_arity():
    assert_rejected(CLASS_WITH_MEMBERS + "let p = new Point(1);", "function")


def test_cls_03_success_this_is_used_inside_a_method():
    assert_accepted(CLASS_WITH_MEMBERS)


def test_cls_03_failure_this_is_used_outside_any_class():
    assert_rejected("let x = this;", "class")


def test_cls_04_success_inherited_member_and_subclass_assignment():
    """Dropping the superclass link must break both lookup and assignment."""
    assert_accepted(
        "class Base { let value: integer; } "
        "class Child : Base { } "
        "let child = new Child(); "
        "let base: Base = child; "
        "let value: integer = child.value;"
    )


def test_cls_04_success_superclass_can_be_declared_after_subclass():
    """The class prepass must resolve a forward superclass declaration."""
    assert_accepted(
        "class Child : Base { } "
        "class Base { let value: integer; } "
        "let child = new Child(); let value: integer = child.value;"
    )


def test_cls_04_success_subclass_body_sees_later_superclass_members():
    """All class interfaces must exist before the first class body is checked."""
    assert_accepted(
        "class Child : Base { "
        "function read(): integer { return this.value; } } "
        "class Base { let value: integer; } "
        "let child = new Child(); let value: integer = child.read();"
    )


def test_cls_04_failure_unknown_superclass_is_reported():
    assert_rejected("class Child : Missing { }", "class")


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


def test_ant_06_delivery_grammar_and_profile_accept_a_complete_program():
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


def test_delivery_demonstration_file_exercises_the_hardened_features():
    """An empty or trivial presentation fixture must not pass this contract."""
    source = (REPO_ROOT / "tests" / "cps" / "demostracion-valida.cps").read_text(
        encoding="utf-8"
    )

    result = assert_accepted(source)

    names = {
        symbol.name for symbol in result.semantic_result.symbol_table.global_scope.symbols
    }
    assert {"BaseCounter", "Counter", "isEven", "isOdd", "counter"} <= names


def test_ant_06_delivery_grammar_rejects_a_program_with_mixed_errors():
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
