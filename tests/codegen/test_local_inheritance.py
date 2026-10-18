"""Local inheritance must retain lexical bindings through verified TAC."""

import pytest

from src.codegen.ir import OpCode
from src.codegen.pipeline import compile_compiscript


def test_local_inheritance_preserves_base_offsets_and_static_method_calls():
    result = compile_compiscript(
        "function f():integer { class A { let x:integer=1; "
        "function m():integer { return this.x; } } "
        "class B:A { let y:integer=2; } class C:B { let z:integer=3; } "
        "let c:C=new C(); let a:A=c; return c.m()+c.y+c.z+a.x; } let r=f();"
    )
    assert result.accepted, result.failed_stage
    ir = result.intermediate_result
    layout = ir.layouts.class_layout("C")
    assert [(f.symbol.name, f.offset) for f in layout.all_fields] == [
        ("x", 0), ("y", 8), ("z", 16),
    ]
    procedure = next(p for p in ir.program.procedures if p.label.value == "fn_f")
    assert [i.arg1.value for i in procedure.instructions if i.opcode is OpCode.CALL] == [
        "f.C.constructor", "f.A.m",
    ]
    assert all(i.source_location is not None for i in procedure.instructions)


def test_inherited_local_initializer_reads_the_environment_retained_by_its_base():
    result = compile_compiscript(
        "function f():integer { let n:integer=7; "
        "class A { let x:integer=n; function m():integer { return x; } } "
        "class B:A {} let b=new B(); return b.m(); } let r=f();"
    )
    assert result.accepted, result.intermediate_result.diagnostics
    ir = result.intermediate_result
    base = ir.layouts.class_layout("A")
    child = ir.layouts.class_layout("B")
    assert child.superclass is base
    constructor = next(
        p for p in ir.program.procedures if p.label.value == child.constructor_label
    )
    (read,) = [i for i in constructor.instructions if i.opcode is OpCode.ENV_GET]
    (environment,) = [
        i for i in constructor.instructions
        if i.opcode is OpCode.FIELD_GET and i.arg2.value == base.environment_offset
    ]
    assert read.arg1 == environment.result
    (write,) = [i for i in constructor.instructions if i.opcode is OpCode.FIELD_SET]
    assert write.arg2.value == 0 and write.result == read.result


@pytest.mark.parametrize("construction", [
    "let b=new B(); return b.x+b.y+b.m();",
    "function h():integer { let b=new B(); return b.x+b.y+b.m(); } return h();",
])
def test_subclass_construction_forwards_environments_of_all_ancestor_classes(construction):
    result = compile_compiscript(
        "function f():integer { let n:integer=7; "
        "class A { let x:integer=n; function m():integer { return x; } } "
        "function g():integer { let k:integer=2; class B:A { let y:integer=k; } "
        f"{construction} }} return g(); }} let r=f();"
    )
    assert result.accepted, result.intermediate_result.diagnostics
    ir = result.intermediate_result
    assert ir.layouts.frame_by_label("fn_f.g").needs_env
    child = ir.layouts.class_layout("B")
    base = ir.layouts.class_layout("A")
    assert child.environment_offset != base.environment_offset
    constructor = next(
        p for p in ir.program.procedures if p.label.value == child.constructor_label
    )
    reads = [i for i in constructor.instructions if i.opcode is OpCode.ENV_GET]
    assert len(reads) == 2
    base_env = next(
        i.result for i in constructor.instructions
        if i.opcode is OpCode.FIELD_GET and i.arg2.value == base.environment_offset
    )
    assert reads[0].arg1 == base_env
    assert reads[1].arg1 == constructor.parameters[1]


@pytest.mark.parametrize("initializer", ["n", "h()"])
def test_explicit_subclass_constructor_keeps_the_inherited_initializer_context(initializer):
    result = compile_compiscript(
        "function f():integer { let n:integer=7; function h():integer { return n; } "
        f"class A {{ let x:integer={initializer}; }} class B:A {{ let y:integer=2; "
        "function constructor(k:integer) { this.y=k; } } "
        "let b=new B(3); return b.x+b.y; } let r=f();"
    )
    assert result.accepted, result.failed_stage
    ir = result.intermediate_result
    child = ir.layouts.class_layout("B")
    constructor = next(
        p for p in ir.program.procedures if p.label.value == child.constructor_label
    )
    writes = [i for i in constructor.instructions if i.opcode is OpCode.FIELD_SET]
    assert [i.arg2.value for i in writes] == [0, 16, 16]
    assert writes[-1].result == constructor.parameters[-1]


def test_invalid_inherited_member_stops_before_tac():
    result = compile_compiscript(
        "function f() { class A {} class B:A {} let b=new B(); let x=b.missing; } f();"
    )
    assert result.failed_stage == "semantic"
    assert result.intermediate_result is None and result.tac == ""
    assert any("missing" in d.message for d in result.semantic_result.diagnostics)
