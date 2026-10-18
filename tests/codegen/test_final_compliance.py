"""Regressions found in the final, cross-block delivery audit."""

import pytest

from src.codegen.ir import IRProcedure, IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.pipeline import compile_compiscript
from src.codegen.verifier import IRVerifier
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import FLOAT, INTEGER


def accepted(source):
    result = compile_compiscript(source)
    diagnostics = (
        result.intermediate_result.diagnostics if result.intermediate_result
        else result.semantic_result and result.semantic_result.diagnostics
    )
    assert result.accepted, (result.failed_stage, diagnostics)
    return result.intermediate_result


@pytest.mark.parametrize("body", [
    "function f(t0: integer): integer { return t0 + 1; } let r = f(1);",
    "function f(): integer { let t0: integer = 1; return t0 + 1; } let r = f();",
    "function f(t0: integer): integer { function g(): integer { return t0 + 1; } return g(); } let r=f(1);",
])
def test_user_temporary_names_never_collide_with_frame_slots(body):
    ir = accepted(body)
    for frame in ir.activation_records:
        assert len({slot.name for slot in frame.slots}) == len(frame.slots)
        assert frame.temporary_capacity >= next(
            (p.temporary_peak for p in ir.program.procedures if p.label.value == frame.label), 0
        )


def test_shadowed_classes_keep_distinct_symbols_fields_and_constructors():
    ir = accepted(
        "class C { let a: integer = 1; } "
        "{ class C { let b: float = 2.0; } let y = new C(); } let x = new C();"
    )
    classes = tuple(ir.layouts.classes.values())
    assert len(classes) == 2
    assert classes[0].symbol is not classes[1].symbol
    assert {layout.fields[0].name for layout in classes} == {"a", "b"}
    assert len({p.label.value for p in ir.program.procedures}) == 2
    for layout in classes:
        assert ir.layouts.class_layout(layout.symbol) is layout
        assert ir.layouts.class_layout(layout.symbol.type) is layout
    with pytest.raises(LookupError, match="ambiguous"):
        ir.layouts.class_layout("C")


def test_call_arity_is_checked_against_the_known_procedure():
    loc = SourceLocation(1, 1)
    label = Operand(OperandKind.LABEL, "f")
    parameter = Operand(OperandKind.SYMBOL, "p", INTEGER)
    zero = Operand(OperandKind.CONSTANT, 0, INTEGER)
    procedure = IRProcedure(label, (parameter,), (
        Instruction(OpCode.RETURN, parameter, source_location=loc),
    ))
    program = IRProgram((Instruction(OpCode.CALL, label, zero, source_location=loc),), (procedure,))
    assert "IR-CALL-SIGNATURE" in {d.code for d in IRVerifier().verify(program)}


@pytest.mark.parametrize("condition", ["true", "false"])
def test_mixed_ternary_converts_integer_branch_before_the_join(condition):
    ir = accepted(
        f"let i: integer = 2; let f: float = 2.5; let x: float = {condition} ? i : f;"
    )
    code = ir.program.global_code
    casts = [item for item in code if item.opcode is OpCode.CAST]
    assert len(casts) == 1
    assert casts[0].arg1.type == INTEGER and casts[0].result.type == FLOAT
    assert not any(
        item.opcode is OpCode.COPY and item.arg1.type == INTEGER and item.result.type == FLOAT
        for item in code
    )


@pytest.mark.parametrize("body", [
    "return g();",
    "let saved = g; return saved();",
    "return k();",
])
def test_sibling_function_dependencies_propagate_environments(body):
    ir = accepted(
        "function outer(): integer { let x: integer = 1; "
        "function g(): integer { return x; } "
        "function k(): integer { return g(); } "
        f"function h(): integer {{ {body} }} return h(); }} let r = outer();"
    )
    assert ir.layouts.frame_by_label("fn_outer.h").needs_env
    assert ir.layouts.frame_by_label("fn_outer.k").needs_env
    procedure = next(p for p in ir.program.procedures if p.label.value == "fn_outer.h")
    assert any(i.opcode is OpCode.CLOSURE for i in procedure.instructions)


@pytest.mark.parametrize("member", [
    "function m(): integer { return x; }",
    "let y: integer; function constructor() { y = x; } function m(): integer { return y; }",
    "let y: integer = x; function m(): integer { return y; }",
])
def test_local_class_captures_are_carried_by_the_instance(member):
    ir = accepted(
        f"function f(): integer {{ let x: integer = 7; class C {{ {member} }} "
        "let c = new C(); return c.m(); } let r = f();"
    )
    frame = ir.layouts.frame_by_label("fn_f")
    assert frame.environment is not None and frame.environment.heap
    constructor = next(p for p in ir.program.procedures if p.label.value.endswith("C.constructor"))
    for procedure in ir.program.procedures:
        for item in procedure.instructions:
            for operand in (item.arg1, item.arg2, item.result):
                if operand is not None and operand.kind is OperandKind.SYMBOL:
                    address = operand.value
                    if getattr(address, "name", None) == "x":
                        assert address.scope == procedure.label.value
    assert any(i.opcode is OpCode.FIELD_SET for i in next(
        p for p in ir.program.procedures if p.label.value == "fn_f"
    ).instructions)
    assert constructor is not None


@pytest.mark.parametrize("value", ["this.x", "x", "this.m()"])
def test_nested_functions_capture_the_method_receiver(value):
    ir = accepted(
        "class C { let x: integer = 7; function m(): integer { return x; } "
        f"function f(): integer {{ function g(): integer {{ return {value}; }} return g(); }} }} "
        "let c = new C(); let r = c.f();"
    )
    owner = ir.layouts.frame_by_label("C.f")
    nested = ir.layouts.frame_by_label("fn_C.f.g")
    assert owner.environment is not None
    assert nested.needs_env
    body = next(p.instructions for p in ir.program.procedures if p.label.value == nested.label)
    assert any(i.opcode is OpCode.ENV_GET for i in body)


def test_inherited_field_initializers_keep_the_declaring_symbol_offset():
    ir = accepted(
        "class A { let x: integer = 1; function get(): integer { return x; } } "
        "class B: A { let x: integer = 2; } let b = new B(); let r = b.get();"
    )
    constructor = next(p for p in ir.program.procedures if p.label.value == "B.constructor")
    writes = [i for i in constructor.instructions if i.opcode is OpCode.FIELD_SET]
    assert [(i.arg2.value, i.result.value) for i in writes] == [(0, 1), (8, 2)]


def test_inherited_initializer_calls_keep_the_static_declaration_context():
    ir = accepted(
        "class A { function value(): integer { return 1; } let x: integer = value(); } "
        "class B: A { function value(): integer { return 2; } } let b = new B();"
    )
    constructor = next(p for p in ir.program.procedures if p.label.value == "B.constructor")
    assert [i.arg1.value for i in constructor.instructions if i.opcode is OpCode.CALL] == ["A.value"]


def test_constructing_a_local_class_in_a_nested_function_forwards_its_environment():
    ir = accepted(
        "function f(): integer { let x: integer=7; class C { let y: integer=x; } "
        "function h():integer { let c=new C(); return c.y; } return h(); } let r=f();"
    )
    assert ir.layouts.frame_by_label("fn_f.h").needs_env


def test_two_level_receiver_capture_preserves_the_access_chain():
    ir = accepted(
        "class C { let x:integer=7; function f():integer { "
        "function g():integer { function h():integer { return this.x; } return h(); } "
        "return g(); } } let c=new C(); let r=c.f();"
    )
    frame = ir.layouts.frame_by_label("fn_C.f.g.h")
    assert [(c.symbol.name, c.depth) for c in frame.captures] == [("this", 1)]
