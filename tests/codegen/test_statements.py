"""Declarations, assignments, print and conversions of whole programs (EXP-05, EXP-06, EXT-01)."""

from pathlib import Path

import pytest

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.contracts import CodegenError
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import OpCode, OperandKind
from src.semantic.symbol_table import ScopeKind
from src.semantic.types import FLOAT

CPS = Path(__file__).resolve().parents[1] / "cps"


def opcodes(code):
    return [item.opcode for item in code]


def writes(code, name):
    """COPY instructions whose destination is the symbol called ``name``."""
    return [
        item
        for item in code
        if item.opcode is OpCode.COPY
        and item.result.kind is OperandKind.SYMBOL
        and item.result.value.symbol.name == name
    ]


# -- declarations and assignments -------------------------------------------------


def test_declaration_copies_its_initializer_into_the_resolved_symbol(generate_tac):
    lowered = generate_tac("let a: integer = 1;\nlet b: integer = a;\n")
    code = lowered.unit()
    scope = lowered.run.semantic_result.symbol_table.global_scope
    first, second = code
    assert (first.opcode, first.arg1.value) == (OpCode.COPY, 1)
    assert first.result.value.symbol is scope.resolve_local("a")
    assert second.arg1.value.symbol is scope.resolve_local("a")
    assert second.result.value.symbol is scope.resolve_local("b")
    assert lowered.text.splitlines()[1:] == ["    static[0]@a = 1", "    static[4]@b = static[0]@a"]


def test_shadowing_writes_distinct_slots_chosen_by_symbol_identity(generate_tac):
    """EXP-05: the inner ``n`` and the outer ``n`` never share a destination."""
    lowered = generate_tac(
        "let n: integer = 1;\n{\n  let n: integer = 2;\n  n = 3;\n}\nn = 4;\n"
    )
    stores = writes(lowered.unit(), "n")
    assert [store.arg1.value for store in stores] == [1, 2, 3, 4]
    outer = lowered.run.semantic_result.symbol_table.global_scope.resolve_local("n")
    inner = next(
        symbol
        for scope in lowered.run.semantic_result.symbol_table.iter_scopes()
        if scope.kind is ScopeKind.BLOCK
        for symbol in scope.symbols
    )
    targets = [store.result.value.symbol for store in stores]
    assert targets[0] is outer and targets[3] is outer
    assert targets[1] is inner and targets[2] is inner
    assert stores[0].result.value.offset != stores[1].result.value.offset


def test_constant_initialization_generates_a_single_copy(generate_tac):
    """EXP-06: a constant is written once, at its declaration."""
    lowered = generate_tac("const limite: integer = 7;\nlet usado: integer = limite;\n")
    (store,) = writes(lowered.unit(), "limite")
    assert store.arg1.value == 7


def test_a_declaration_without_initializer_invents_no_value(generate_tac):
    assert generate_tac("let a: integer;\nlet b;\nlet c: string[];\n").unit() == ()


def test_assignment_statement_copies_then_releases_its_temporary(generate_tac):
    code = generate_tac("let a: integer = 1;\na = a + 2;\n").unit()
    assert opcodes(code) == [
        OpCode.COPY, OpCode.COPY, OpCode.ADD, OpCode.RELEASE, OpCode.COPY, OpCode.RELEASE,
    ]
    assert code[4].result.value.symbol.name == "a" and code[5].arg1 == code[4].arg1


def test_expression_statement_discards_its_value(generate_tac):
    code = generate_tac("let a: integer = 1;\na * 2;\n").unit()
    (product,) = [item for item in code if item.opcode is OpCode.MUL]
    assert code[-1].opcode is OpCode.RELEASE and code[-1].arg1 == product.result
    assert not writes(code[1:], "a")


# -- print and conversions --------------------------------------------------------


def test_print_calls_the_runtime_procedure_with_one_parameter(generate_tac):
    """EXT-01: print is a call to the abstract runtime, not an inlined effect."""
    lowered = generate_tac('let a: integer = 2;\nprint(a);\nprint("hola");\n')
    code = lowered.unit()
    assert opcodes(code)[1:] == [OpCode.PARAM, OpCode.CALL, OpCode.PARAM, OpCode.CALL]
    call = code[2]
    assert (call.arg1.kind, call.arg1.value, call.arg2.value, call.result) == (
        OperandKind.LABEL, "print", 1, None,
    )
    assert lowered.text.splitlines()[-2:] == ['    param "hola"', "    call print, 1"]


def test_integer_constant_widened_to_float_is_converted_at_compile_time(generate_tac):
    (store,) = generate_tac("let f: float = 2;\n").unit()
    assert store.arg1.value == 2.0 and type(store.arg1.value) is float
    assert store.arg1.type == FLOAT


def test_integer_value_widened_to_float_uses_an_explicit_cast(generate_tac):
    lowered = generate_tac("let a: integer = 3;\nlet f: float = a;\n")
    code = lowered.unit()
    cast = next(item for item in code if item.opcode is OpCode.CAST)
    assert cast.arg1.value.symbol.name == "a" and cast.arg2.value == "float"
    assert cast.result.type == FLOAT
    assert writes(code, "f")[0].arg1 == cast.result
    assert "    t0 = cast float static[0]@a" in lowered.text


def test_mixed_arithmetic_casts_the_integer_operand(generate_tac):
    code = generate_tac("let a: integer = 3;\nlet f: float = a + 2.5;\n").unit()
    cast_index = opcodes(code).index(OpCode.CAST)
    add = next(item for item in code if item.opcode is OpCode.ADD)
    assert code.index(add) > cast_index
    assert add.arg1 == code[cast_index].result and add.arg2.value == 2.5
    assert add.result.type == FLOAT


def test_same_typed_arithmetic_keeps_daniels_lowering(generate_tac):
    code = generate_tac("let a: integer = 3;\nlet b: integer = a * 2 + 1;\n").unit()
    assert OpCode.CAST not in opcodes(code)
    assert [op for op in opcodes(code) if op in (OpCode.MUL, OpCode.ADD)] == [
        OpCode.MUL, OpCode.ADD,
    ]


# -- reachability, coverage and errors --------------------------------------------


def test_statements_after_an_unconditional_transfer_are_not_emitted(generate_tac):
    """PIPE-03: the semantic warning program still produces TAC, without dead code."""
    source = (CPS / "advertencias" / "GEN-01-codigo-inalcanzable-despues-de-break.cps").read_text(
        encoding="utf8"
    )
    code = generate_tac(source).unit()
    assert OpCode.PARAM not in opcodes(code) and OpCode.CALL not in opcodes(code)


def test_unsupported_statement_reports_its_location(compile_facts):
    _, facts = compile_facts("let a: integer = 1;\n")
    generator = CompiscriptCodeGenerator(facts)
    mystery = ParseTreeNode("mystery", rule_name="mystery", line=7, column=3)
    with pytest.raises(CodegenError, match="IRGEN-UNSUPPORTED-NODE") as error:
        generator.lower_statement(mystery)
    assert (error.value.location.line, error.value.location.column) == (7, 3)


def test_a_generator_lowers_exactly_one_program(compile_facts):
    run, facts = compile_facts("let a: integer = 1;\n")
    generator = CompiscriptCodeGenerator(facts)
    generator.generate(run.syntax_result.tree)
    with pytest.raises(RuntimeError, match="exactly one program"):
        generator.generate(run.syntax_result.tree)


def test_global_temporary_peak_reserves_global_frame_slots(generate_tac):
    """TMP-05: global code reserves exactly its peak of live temporaries."""
    lowered = generate_tac("let a: integer = 1;\nlet b: integer = (a + 1) * (a + 2);\n")
    frame = lowered.layouts.global_frame
    assert frame.temporary_capacity == 3
    assert [slot.name for slot in frame.temporaries] == ["t0", "t1", "t2"]
