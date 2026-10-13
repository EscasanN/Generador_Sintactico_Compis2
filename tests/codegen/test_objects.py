"""Objects, constructors, fields, methods, this and inheritance (CLS-02…CLS-06, EXT-05)."""

from pathlib import Path

import pytest

from src.codegen.contracts import CodegenError
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import OpCode, OperandKind

CPS = Path(__file__).resolve().parents[1] / "cps"


def find(code, opcode):
    return [item for item in code if item.opcode is opcode]


def fixture(name):
    return (CPS / "validos" / name).read_text(encoding="utf8")


def is_this(operand):
    return operand.kind is OperandKind.SYMBOL and operand.value.name == "this"


# -- creation and constructors ----------------------------------------------------


def test_new_reserves_the_instance_and_calls_the_constructor_with_this(generate_tac):
    """CLS-02: object_new, then the instance as the first parameter."""
    lowered = generate_tac(fixture("CLS-01-miembros.cps"))
    code = lowered.unit()
    (created,) = find(code, OpCode.OBJECT_NEW)
    layout = lowered.layouts.class_layout("Punto")
    assert (created.arg1.value, created.arg2.value) == ("Punto", layout.size)
    start = code.index(created)
    params = code[start + 1:start + 4]
    assert [item.opcode for item in params] == [OpCode.PARAM] * 3
    assert params[0].arg1 == created.result
    assert [item.arg1.value for item in params[1:]] == [2, 3]
    call = code[start + 4]
    assert (call.opcode, call.arg1.value, call.arg2.value, call.result) == (
        OpCode.CALL, "Punto.constructor", 3, None,
    )
    assert code[start + 5].result.value.symbol.name == "punto"
    assert "    t0 = object_new Punto, 8" in lowered.text


def test_constructor_writes_fields_through_the_hidden_this(generate_tac):
    """CLS-03: the explicit constructor stores each parameter at its field offset."""
    lowered = generate_tac(fixture("CLS-01-miembros.cps"))
    (procedure,) = [p for p in lowered.program.procedures if p.label.value == "Punto.constructor"]
    assert [op.value.name for op in procedure.parameters] == ["this", "x", "y"]
    stores = find(procedure.instructions, OpCode.FIELD_SET)
    assert [(is_this(s.arg1), s.arg2.value, s.result.value.name) for s in stores] == [
        (True, 0, "x"), (True, 4, "y"),
    ]


def test_field_reads_and_method_calls_pass_the_receiver(generate_tac):
    """CLS-03 and CLS-04: field_get by offset; a method gets its receiver first."""
    lowered = generate_tac(fixture("CLS-01-miembros.cps"))
    code = lowered.unit()
    (read,) = find(code, OpCode.FIELD_GET)
    assert read.arg1.value.symbol.name == "punto" and read.arg2.value == 0
    method_call = next(item for item in find(code, OpCode.CALL) if item.arg1.value == "Punto.suma")
    receiver = code[code.index(method_call) - 1]
    assert receiver.opcode is OpCode.PARAM and receiver.arg1.value.symbol.name == "punto"
    assert method_call.arg2.value == 1 and method_call.result is not None
    body = lowered.unit("Punto.suma")
    assert [(is_this(i.arg1), i.arg2.value) for i in find(body, OpCode.FIELD_GET)] == [
        (True, 0), (True, 4),
    ]


def test_implicit_constructor_is_synthesized_with_field_initializers(generate_tac):
    """CLS-05: a class without constructor still answers new C()."""
    lowered = generate_tac(fixture("CLS-02-constructor.cps"))
    body = lowered.unit("SinConstructor.constructor")
    assert [item.opcode for item in body] == [OpCode.FIELD_SET, OpCode.RETURN]
    assert is_this(body[0].arg1) and body[0].result.value == "vacio"
    calls = [item for item in find(lowered.unit(), OpCode.CALL)]
    assert [(c.arg1.value, c.arg2.value) for c in calls] == [
        ("ConConstructor.constructor", 2), ("SinConstructor.constructor", 1),
    ]
    frame = lowered.layouts.frame_by_label("SinConstructor.constructor")
    assert [slot.name for slot in frame.hidden_parameters] == ["this"]
    assert frame.function is None and frame.level == 1


def test_explicit_constructor_runs_field_initializers_before_its_body(generate_tac):
    lowered = generate_tac(
        "class C {\n"
        "  let a: integer = 1;\n"
        "  function constructor(b: integer) { this.a = b; }\n"
        "}\n"
        "let c = new C(5);\n"
    )
    stores = find(lowered.unit("C.constructor"), OpCode.FIELD_SET)
    assert [store.result.kind for store in stores] == [OperandKind.CONSTANT, OperandKind.SYMBOL]
    assert stores[0].result.value == 1 and stores[1].result.value.name == "b"


# -- inheritance ------------------------------------------------------------------


def test_inherited_fields_keep_base_offsets_and_methods_resolve_statically(generate_tac):
    """CLS-06 and EXT-05 with tests/cps/validos/CLS-04-herencia.cps."""
    lowered = generate_tac(fixture("CLS-04-herencia.cps"))
    (read,) = find(lowered.unit("Hija.leer"), OpCode.FIELD_GET)
    assert is_this(read.arg1) and read.arg2.value == 0
    assert lowered.layouts.class_layout("Hija").field_offset("valor") == 0
    calls = [c.arg1.value for c in find(lowered.unit(), OpCode.CALL)]
    assert calls == ["Hija.constructor", "Hija.leer"]


def test_subclass_calls_inherited_method_and_initializes_base_fields_first(generate_tac):
    lowered = generate_tac(
        "class Base {\n"
        "  let a: integer = 1;\n"
        "  function saludo(): string { return \"hola\"; }\n"
        "}\n"
        "class Hija : Base {\n"
        "  let b: integer = 2;\n"
        "  function usar(): string { return this.saludo(); }\n"
        "}\n"
        "let h = new Hija();\n"
        "let s: string = h.saludo();\n"
    )
    stores = find(lowered.unit("Hija.constructor"), OpCode.FIELD_SET)
    assert [(store.arg2.value, store.result.value) for store in stores] == [(0, 1), (8, 2)]
    (inner,) = find(lowered.unit("Hija.usar"), OpCode.CALL)
    assert inner.arg1.value == "Base.saludo"
    outer = [c.arg1.value for c in find(lowered.unit(), OpCode.CALL)]
    assert outer == ["Hija.constructor", "Base.saludo"]


def test_method_declared_after_its_use_is_called_by_its_class_label(generate_tac):
    """Semantics may record a provisional member Symbol; codegen resolves by name."""
    lowered = generate_tac(
        "class A {\n"
        "  function primero(): integer { return this.segundo() + 1; }\n"
        "  function segundo(): integer { return 2; }\n"
        "}\n"
    )
    (call,) = find(lowered.unit("A.primero"), OpCode.CALL)
    assert call.arg1.value == "A.segundo" and call.arg2.value == 1


# -- this and member access forms -------------------------------------------------


def test_bare_member_names_inside_a_class_mean_this(generate_tac):
    lowered = generate_tac(
        "class Caja {\n"
        "  let valor: integer;\n"
        "  function leer(): integer { return valor; }\n"
        "  function doble(): integer { return leer() * 2; }\n"
        "}\n"
    )
    (read,) = find(lowered.unit("Caja.leer"), OpCode.FIELD_GET)
    assert is_this(read.arg1) and read.arg2.value == 0
    (call,) = find(lowered.unit("Caja.doble"), OpCode.CALL)
    receiver = lowered.unit("Caja.doble")[0]
    assert call.arg1.value == "Caja.leer" and is_this(receiver.arg1)


def test_field_assignment_expression_uses_field_set_and_yields_the_value(generate_tac):
    """EXP-08: a member target is a store, never a plain copy."""
    lowered = generate_tac(
        "class P { let x: integer; }\nlet p = new P();\nlet y: integer = (p.x = 5);\np.x = 6;\n"
    )
    code = lowered.unit()
    stores = find(code, OpCode.FIELD_SET)
    assert [(s.arg1.value.symbol.name, s.arg2.value, s.result.value) for s in stores] == [
        ("p", 0, 5), ("p", 0, 6),
    ]
    copy_y = next(item for item in code if item.opcode is OpCode.COPY and item.result.value.symbol.name == "y")
    assert copy_y.arg1.value == 5


def test_this_in_the_full_demonstration_program(generate_tac):
    lowered = generate_tac((CPS / "demostracion-valida.cps").read_text(encoding="utf8"))
    description = lowered.unit("Counter.description")
    assert is_this(description[0].arg1) and description[1].arg1.value == "BaseCounter.label"
    assert "procedure Counter.constructor(parameter:Counter.constructor[32]@this, " in lowered.text


# -- failures ---------------------------------------------------------------------


def test_static_member_access_through_a_class_name_is_rejected(compile_facts):
    run, facts = compile_facts("class C {\n  let v: integer;\n}\nlet x: integer = C.v;\n")
    with pytest.raises(CodegenError, match="IRGEN-UNSUPPORTED-NODE") as error:
        CompiscriptCodeGenerator(facts).generate(run.syntax_result.tree)
    assert error.value.location.line == 4


def test_this_inside_a_function_nested_in_a_method_is_rejected(compile_facts):
    run, facts = compile_facts(
        "class C {\n"
        "  let v: integer;\n"
        "  function m(): integer {\n"
        "    function f(): integer { return this.v; }\n"
        "    return f();\n"
        "  }\n"
        "}\n"
    )
    with pytest.raises(CodegenError, match="IRGEN-THIS-UNAVAILABLE"):
        CompiscriptCodeGenerator(facts).generate(run.syntax_result.tree)
