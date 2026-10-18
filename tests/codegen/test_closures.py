"""Nested functions, environments and captured variables (FUN-07, FUN-08)."""

from pathlib import Path

import pytest

from src.codegen.contracts import CodegenError
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import OpCode, OperandKind

CPS = Path(__file__).resolve().parents[1] / "cps"


def find(code, opcode):
    return [item for item in code if item.opcode is opcode]


def is_hidden_env(operand):
    return operand.kind is OperandKind.SYMBOL and operand.value.name == "env"


def test_real_closure_program_creates_and_uses_an_environment(generate_tac):
    """FUN-07 with tests/cps/validos/FUN-04-closure.cps."""
    source = (CPS / "validos" / "FUN-04-closure.cps").read_text(encoding="utf8")
    lowered = generate_tac(source)
    exterior = lowered.unit("fn_exterior")
    (created,) = find(exterior, OpCode.ENV_NEW)
    assert created.arg1.value == lowered.layouts.frame_by_label("fn_exterior").environment.size
    (stored,) = find(exterior, OpCode.ENV_SET)
    assert (stored.arg1, stored.arg2.value, stored.result.value) == (created.result, 0, 10)
    (closure,) = find(exterior, OpCode.CLOSURE)
    assert (closure.arg1.value, closure.arg2) == ("fn_exterior.interior", created.result)
    (call,) = find(exterior, OpCode.CLOSURE_CALL)
    assert call.arg1 == closure.result and call.arg2.value == 0
    interior = lowered.unit("fn_exterior.interior")
    (read,) = find(interior, OpCode.ENV_GET)
    assert is_hidden_env(read.arg1) and read.arg2.value == (0, 0)
    assert "procedure fn_exterior.interior(parameter:fn_exterior.interior[32]@env):" in lowered.text
    assert "    t0 = env_get parameter:fn_exterior.interior[32]@env, 0:0" in lowered.text


def test_two_level_capture_follows_the_access_link_never_the_caller(generate_tac):
    """FUN-08: x lives two functions out (depth 1), y one function out (depth 0)."""
    lowered = generate_tac(
        "function a(): integer {\n"
        "  let x: integer = 1;\n"
        "  function b(): integer {\n"
        "    let y: integer = 2;\n"
        "    function c(): integer { return x + y; }\n"
        "    return c();\n"
        "  }\n"
        "  return b();\n"
        "}\n"
    )
    reads = find(lowered.unit("fn_a.b.c"), OpCode.ENV_GET)
    assert [read.arg2.value for read in reads] == [(1, 0), (0, 0)]
    assert all(is_hidden_env(read.arg1) for read in reads)
    middle = lowered.unit("fn_a.b")
    created = find(middle, OpCode.ENV_NEW)[0].result
    link = find(middle, OpCode.ENV_SET)[0]
    frame = lowered.layouts.frame_by_label("fn_a.b")
    assert (link.arg1, link.arg2.value) == (created, frame.environment.parent_offset)
    assert is_hidden_env(link.result)
    # inner procedures never address the owner's frame directly
    owner_frames = {"fn_a", "fn_a.b"}
    for item in lowered.unit("fn_a.b.c"):
        for operand in (item.arg1, item.arg2, item.result):
            if operand is not None and operand.kind is OperandKind.SYMBOL:
                assert operand.value.scope not in owner_frames


def test_captured_variables_are_shared_by_reference(generate_tac):
    """The owner and the closure both write through the environment."""
    lowered = generate_tac(
        "function contador(): integer {\n"
        "  let c: integer = 0;\n"
        "  function inc(): integer { c = c + 1; return c; }\n"
        "  c = 10;\n"
        "  return inc();\n"
        "}\n"
    )
    owner = lowered.unit("fn_contador")
    environment = find(owner, OpCode.ENV_NEW)[0].result
    writes = [item for item in find(owner, OpCode.ENV_SET) if item.arg1 == environment]
    assert [item.result.value for item in writes] == [0, 10]
    assert not [item for item in owner if item.opcode is OpCode.COPY and item.result.kind is OperandKind.SYMBOL]
    inner = lowered.unit("fn_contador.inc")
    (write,) = find(inner, OpCode.ENV_SET)
    assert is_hidden_env(write.arg1) and write.arg2.value == (0, 0)


def test_captured_parameter_is_copied_into_the_environment_by_the_prologue(generate_tac):
    lowered = generate_tac(
        "function outer(p: integer): integer {\n"
        "  function inner(): integer { return p; }\n"
        "  return inner();\n"
        "}\n"
    )
    code = lowered.unit("fn_outer")
    assert code[0].opcode is OpCode.ENV_NEW
    copy = code[1]
    assert copy.opcode is OpCode.ENV_SET and copy.result.value.name == "p"
    assert copy.result.value.storage == "parameter"


def test_escaping_function_value_and_indirect_call(generate_tac):
    """A function stored in a variable is a closure; calling it uses closure_call."""
    lowered = generate_tac(
        "function f(): integer {\n"
        "  let x: integer = 1;\n"
        "  function g(): integer { return x; }\n"
        "  let guardada = g;\n"
        "  return guardada();\n"
        "}\n"
        "function suma(a: integer, b: integer): integer { return a + b; }\n"
        "let h = suma;\n"
        "let r: integer = h(1, 2);\n"
    )
    assert lowered.layouts.frame_by_label("fn_f").environment.heap is True
    body = lowered.unit("fn_f")
    (closure,) = find(body, OpCode.CLOSURE)
    assert closure.arg1.value == "fn_f.g"
    (call,) = find(body, OpCode.CLOSURE_CALL)
    assert call.arg1.kind is OperandKind.SYMBOL and call.arg1.value.name == "guardada"
    global_code = lowered.unit()
    (value,) = find(global_code, OpCode.CLOSURE)
    assert (value.arg1.value, value.arg2.value) == ("fn_suma", None)
    (indirect,) = find(global_code, OpCode.CLOSURE_CALL)
    assert indirect.arg2.value == 2
    assert "closure fn_suma, null" in lowered.text


def test_recursive_closure_closes_over_the_environment_it_received(generate_tac):
    lowered = generate_tac(
        "function rec(n: integer): integer {\n"
        "  let k: integer = n;\n"
        "  function interna(m: integer): integer {\n"
        "    if (m <= 0) { return k; }\n"
        "    return interna(m - 1);\n"
        "  }\n"
        "  return interna(n);\n"
        "}\n"
    )
    inner = lowered.unit("fn_rec.interna")
    (closure,) = find(inner, OpCode.CLOSURE)
    assert closure.arg1.value == "fn_rec.interna" and is_hidden_env(closure.arg2)


def test_nested_function_without_captures_is_a_plain_call(generate_tac):
    lowered = generate_tac(
        "function f(): integer {\n"
        "  function g(): integer { return 1; }\n"
        "  return g();\n"
        "}\n"
    )
    body = lowered.unit("fn_f")
    assert not find(body, OpCode.CLOSURE) and not find(body, OpCode.ENV_NEW)
    (call,) = find(body, OpCode.CALL)
    assert call.arg1.value == "fn_f.g"


def test_a_caller_inherits_the_environment_needed_by_a_sibling(generate_tac):
    """A function dependency needs the same lexical chain as a direct capture."""
    lowered = generate_tac(
        "function outer(): integer {\n"
        "  let x: integer = 1;\n"
        "  function g(): integer { return x; }\n"
        "  function h(): integer { return g(); }\n"
        "  return h();\n"
        "}\n"
    )
    assert lowered.layouts.frame_by_label("fn_outer.h").needs_env
    (closure,) = find(lowered.unit("fn_outer.h"), OpCode.CLOSURE)
    assert closure.arg1.value == "fn_outer.g" and is_hidden_env(closure.arg2)
