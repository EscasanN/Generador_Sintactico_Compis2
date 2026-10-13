"""Labels and jumps for if, loops, switch, break/continue and try/catch (CTL-01…CTL-08, EXT-07)."""

import pytest

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.contracts import CodegenError
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import OpCode, OperandKind
from src.semantic.types import STRING

JUMPS = (OpCode.GOTO, OpCode.IF_TRUE, OpCode.IF_FALSE)


def opcodes(code):
    return [item.opcode for item in code]


def label_index(code, prefix):
    """Index of the LABEL whose name starts with ``prefix`` (exactly one expected)."""
    (index,) = [
        i
        for i, item in enumerate(code)
        if item.opcode is OpCode.LABEL and str(item.result.value).startswith(prefix)
    ]
    return index


def jumps_to(code, prefix):
    return [
        i
        for i, item in enumerate(code)
        if item.opcode in JUMPS and str(item.result.value).startswith(prefix)
    ]


def calls_with(code, constant):
    """Indexes of ``param <constant>`` instructions (used to locate branch bodies)."""
    return [
        i
        for i, item in enumerate(code)
        if item.opcode is OpCode.PARAM
        and item.arg1.kind is OperandKind.CONSTANT
        and item.arg1.value == constant
    ]


# -- conditionals -----------------------------------------------------------------


def test_if_without_else_skips_the_body_when_false(generate_tac):
    """CTL-01: a false condition jumps straight to the end label."""
    code = generate_tac("let a: integer = 1;\nif (a < 2) {\n  print(10);\n}\n").unit()
    (branch,) = [i for i, item in enumerate(code) if item.opcode is OpCode.IF_FALSE]
    end = label_index(code, "if_end")
    assert code[branch].result == code[end].result
    (body,) = calls_with(code, 10)
    assert branch < body < end


def test_if_else_executes_exactly_one_branch(generate_tac):
    """CTL-02: the true branch jumps over the else branch."""
    lowered = generate_tac(
        "let a: integer = 1;\nif (a < 2) {\n  print(10);\n} else {\n  print(20);\n}\n"
    )
    code = lowered.unit()
    else_label, end = label_index(code, "if_else"), label_index(code, "if_end")
    (then_body,), (else_body,) = calls_with(code, 10), calls_with(code, 20)
    (skip,) = jumps_to(code, "if_end")
    assert code[skip].opcode is OpCode.GOTO
    assert then_body < skip < else_label < else_body < end
    (branch,) = [i for i, item in enumerate(code) if item.opcode is OpCode.IF_FALSE]
    assert code[branch].result == code[else_label].result


def test_the_condition_temporary_is_released_after_the_join(generate_tac):
    """TMP-04: a value crossing both branches lives until the merge point."""
    code = generate_tac(
        "let a: integer = 1;\nif (a < 2) {\n  print(1);\n} else {\n  print(2);\n}\n"
    ).unit()
    (branch,) = [i for i, item in enumerate(code) if item.opcode is OpCode.IF_FALSE]
    condition = code[branch].arg1
    (release,) = [
        i for i, item in enumerate(code) if item.opcode is OpCode.RELEASE and item.arg1 == condition
    ]
    assert release == label_index(code, "if_end") + 1


# -- loops ------------------------------------------------------------------------


def test_while_checks_its_condition_before_every_iteration(generate_tac):
    """CTL-03 and CTL-08: continue returns to the condition, never into the body."""
    code = generate_tac(
        "let a: integer = 0;\nwhile (a < 10) {\n  a = a + 1;\n  continue;\n}\n"
    ).unit()
    start = label_index(code, "while_cond")
    end = label_index(code, "while_end")
    (exit_branch,) = jumps_to(code, "while_end")
    assert code[exit_branch].opcode is OpCode.IF_FALSE and start < exit_branch < end
    back_edges = jumps_to(code, "while_cond")
    assert back_edges and all(code[i].opcode is OpCode.GOTO for i in back_edges)
    # the explicit continue is the only back edge: the closing goto would be dead code
    assert len(back_edges) == 1 and back_edges[0] == end - 1


def test_do_while_runs_the_body_before_its_condition(generate_tac):
    """CTL-04: the body label comes first; the condition jumps back while true."""
    code = generate_tac(
        "let a: integer = 3;\ndo {\n  a = a - 1;\n  if (a == 1) {\n    continue;\n  }\n} while (a > 0);\n"
    ).unit()
    body, condition, end = (
        label_index(code, "do_body"), label_index(code, "do_cond"), label_index(code, "do_end"),
    )
    assert body < condition < end
    (back,) = jumps_to(code, "do_body")
    assert code[back].opcode is OpCode.IF_TRUE and condition < back < end
    (continue_jump,) = jumps_to(code, "do_cond")
    assert body < continue_jump < condition


@pytest.mark.parametrize(
    "header,alternative,has_condition,has_update",
    [
        ("for (let i: integer = 0; i < 3; i = i + 1)", "ForCondUpdate", True, True),
        ("for (let i: integer = 0; i < 3;)", "ForCondNoUpdate", True, False),
        ("for (let i: integer = 0; ; i = i + 1)", "ForNoCondUpdate", False, True),
        ("for (;;)", "ForNoCondNoUpdate", False, False),
    ],
)
def test_the_four_for_forms(generate_tac, walk_tree, header, alternative, has_condition, has_update):
    """CTL-05: optional condition and update; continue targets the update label."""
    body = "  if (true) {\n    continue;\n  }\n  break;\n"
    lowered = generate_tac(f"{header} {{\n{body}}}\n")
    assert any(node.alternative == alternative for node in walk_tree(lowered.run.syntax_result.tree))
    code = lowered.unit()
    condition = label_index(code, "for_cond")
    update = label_index(code, "for_update")
    end = label_index(code, "for_end")
    assert condition < update < end
    exits = [i for i in jumps_to(code, "for_end") if code[i].opcode is OpCode.IF_FALSE]
    assert bool(exits) is has_condition
    assert (OpCode.ADD in opcodes(code[update:end])) is has_update
    (continue_jump,) = jumps_to(code, "for_update")
    assert condition < continue_jump < update
    assert jumps_to(code, "for_cond") == [end - 1]
    if header.startswith("for (let"):
        initial = next(i for i, item in enumerate(code) if item.opcode is OpCode.COPY)
        assert initial < condition


def test_foreach_reads_by_index_and_continue_increments(generate_tac):
    """LST-04: list_len once, list_get into the iterator, continue goes to the step."""
    lowered = generate_tac(
        "let xs: integer[];\nforeach (x in xs) {\n  if (x == 2) {\n    continue;\n  }\n  print(x);\n}\n"
    )
    code = lowered.unit()
    assert opcodes(code).count(OpCode.LIST_LEN) == 1
    (get,) = [item for item in code if item.opcode is OpCode.LIST_GET]
    assert get.result.kind is OperandKind.SYMBOL and get.result.value.symbol.name == "x"
    step = label_index(code, "foreach_next")
    increment = code[step + 1]
    assert increment.opcode is OpCode.ADD and increment.arg2.value == 1
    assert increment.result == increment.arg1 == get.arg2
    (continue_jump,) = jumps_to(code, "foreach_next")
    assert continue_jump < step
    assert jumps_to(code, "foreach_cond") == [label_index(code, "foreach_end") - 1]


def test_break_and_continue_use_the_nearest_enclosing_loop(generate_tac):
    """CTL-07 and CTL-08 with nested loops of different kinds."""
    source = (
        "for (let i: integer = 0; i < 3; i = i + 1) {\n"
        "  let j: integer = 0;\n"
        "  while (j < 3) {\n"
        "    j = j + 1;\n"
        "    if (j == 2) {\n      break;\n    }\n"
        "  }\n"
        "  continue;\n"
        "}\n"
    )
    code = generate_tac(source).unit()
    inner_end = label_index(code, "while_end")
    (inner_break,) = [i for i in jumps_to(code, "while_end") if code[i].opcode is OpCode.GOTO]
    assert label_index(code, "while_cond") < inner_break < inner_end
    (outer_continue,) = jumps_to(code, "for_update")
    assert inner_end < outer_continue < label_index(code, "for_update")


# -- switch -----------------------------------------------------------------------


def test_switch_evaluates_the_discriminant_once_and_falls_through(generate_tac):
    """CTL-06: one evaluation, dispatch in source order, no jump between cases."""
    source = (
        "let a: integer = 3;\n"
        "switch (a > 2) {\n"
        "  case true:\n    print(1);\n"
        "  case false:\n    print(2);\n"
        "  default:\n    print(3);\n"
        "}\n"
    )
    code = generate_tac(source).unit()
    assert opcodes(code).count(OpCode.GT) == 1
    comparisons = [item for item in code if item.opcode is OpCode.EQ]
    assert [item.arg2.value for item in comparisons] == [True, False]
    assert comparisons[0].arg1 == comparisons[1].arg1
    assert comparisons[0].result == comparisons[1].result
    dispatch = [i for i, item in enumerate(code) if item.opcode is OpCode.IF_TRUE]
    defined = {
        item.result.value: i for i, item in enumerate(code) if item.opcode is OpCode.LABEL
    }
    case_labels = [defined[code[i].result.value] for i in dispatch]
    assert case_labels == sorted(case_labels) and len(set(case_labels)) == 2
    (to_default,) = jumps_to(code, "switch_default")
    assert code[to_default].opcode is OpCode.GOTO and to_default == dispatch[1] + 1
    (one,), (two,), (three,) = calls_with(code, 1), calls_with(code, 2), calls_with(code, 3)
    assert one < two < three
    assert not [i for i in range(one, two) if code[i].opcode is OpCode.GOTO]


def test_switch_without_default_leaves_through_its_end_label(generate_tac):
    code = generate_tac("let b: boolean = true;\nswitch (b) {\n  case false:\n    print(1);\n}\n").unit()
    (leave,) = jumps_to(code, "switch_end")
    assert code[leave].opcode is OpCode.GOTO
    assert label_index(code, "switch_end") > label_index(code, "switch_case")


def test_break_inside_a_switch_leaves_the_enclosing_loop(generate_tac):
    """break belongs to loops, as in the semantic phase; switch pushes no target."""
    source = (
        "while (true) {\n"
        "  switch (true) {\n    case true:\n      break;\n  }\n"
        "}\n"
    )
    code = generate_tac(source).unit()
    gotos = [i for i in jumps_to(code, "while_end") if code[i].opcode is OpCode.GOTO]
    assert gotos and label_index(code, "switch_case") < gotos[0] < label_index(code, "switch_end")


# -- exceptions -------------------------------------------------------------------


def test_try_catch_emits_high_level_handler_instructions(generate_tac):
    """EXT-07: try_begin installs the handler, catch binds the string variable."""
    lowered = generate_tac(
        'try {\n  print("x");\n} catch (err) {\n  print(err);\n}\n'
    )
    code = lowered.unit()
    begin = code[0]
    assert begin.opcode is OpCode.TRY_BEGIN
    handler = label_index(code, "try_catch")
    assert code[handler].result == begin.result
    assert OpCode.TRY_END in opcodes(code[:handler])
    catch = code[handler + 1]
    assert catch.opcode is OpCode.CATCH and catch.result.value.symbol.name == "err"
    assert catch.result.type == STRING
    assert "    catch static[0]@err" in lowered.text


# -- failures ---------------------------------------------------------------------


def _first(tree, walk, rule):
    return next(node for node in walk(tree) if node.rule_name == rule)


def test_break_and_continue_without_a_loop_are_rejected(compile_facts, walk_tree):
    run, facts = compile_facts("while (true) {\n  if (true) {\n    continue;\n  }\n  break;\n}\n")
    tree = run.syntax_result.tree
    for rule, code in (
        ("breakStatement", "IRGEN-BREAK-OUTSIDE-LOOP"),
        ("continueStatement", "IRGEN-CONTINUE-OUTSIDE-LOOP"),
    ):
        with pytest.raises(CodegenError, match=code):
            CompiscriptCodeGenerator(facts).lower_statement(_first(tree, walk_tree, rule))


def test_loop_targets_are_restored_after_a_generation_error(compile_facts, walk_tree):
    """A failing body still pops its loop destinations."""
    run, facts = compile_facts("// pilas restauradas\nwhile (true) {\n  print(1);\n}\n")
    body = _first(run.syntax_result.tree, walk_tree, "block")
    statement = ParseTreeNode("statement", rule_name="statement", line=3, column=3)
    statement.children.append(ParseTreeNode("mystery", rule_name="mystery", line=3, column=3))
    generator = CompiscriptCodeGenerator(facts)
    body.children.insert(len(body.children) - 1, statement)
    try:
        with pytest.raises(CodegenError, match="IRGEN-UNSUPPORTED-NODE"):
            generator.generate(run.syntax_result.tree)
    finally:
        body.children.remove(statement)
    assert generator.break_targets == [] and generator.continue_targets == []
