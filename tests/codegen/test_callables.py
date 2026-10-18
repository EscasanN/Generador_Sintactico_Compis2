"""Procedures, parameters, calls, returns and recursion (FUN-01, FUN-03…FUN-06, TMP-05)."""

from pathlib import Path

import pytest

from src.codegen.contracts import CodegenError
from src.codegen.generator import CompiscriptCodeGenerator
from src.codegen.ir import OpCode, OperandKind
from src.semantic.types import FLOAT, INTEGER

CPS = Path(__file__).resolve().parents[1] / "cps"


def opcodes(code):
    return [item.opcode for item in code]


def calls(code):
    return [item for item in code if item.opcode in (OpCode.CALL, OpCode.CLOSURE_CALL)]


def labels_of(lowered):
    return [procedure.label.value for procedure in lowered.program.procedures]


# -- procedures -------------------------------------------------------------------


def test_each_function_is_a_separate_procedure_with_its_label(generate_tac):
    """FUN-01: bodies never run by falling through global code."""
    lowered = generate_tac(
        "function uno(): integer { return 1; }\n"
        "function dos(): integer { return 2; }\n"
        "let x: integer = uno() + dos();\n"
    )
    assert labels_of(lowered) == ["fn_uno", "fn_dos"]
    assert OpCode.RETURN not in opcodes(lowered.unit())
    assert [item.arg1.value for item in lowered.unit("fn_uno") if item.opcode is OpCode.RETURN] == [1]
    assert "procedure fn_dos():" in lowered.text


def test_declared_parameters_are_procedure_operands_with_frame_offsets(generate_tac):
    lowered = generate_tac("function f(p: integer, q: float): float { return q; }\n")
    (procedure,) = lowered.program.procedures
    assert [(op.value.name, op.value.offset, op.value.scope) for op in procedure.parameters] == [
        ("p", 32, "fn_f"), ("q", 40, "fn_f"),
    ]
    assert all(op.kind is OperandKind.SYMBOL for op in procedure.parameters)
    assert "procedure fn_f(parameter:fn_f[32]@p, parameter:fn_f[40]@q):" in lowered.text


def test_arguments_are_evaluated_and_passed_left_to_right(generate_tac):
    """FUN-03: PARAM order follows the source; CALL carries the argument count."""
    lowered = generate_tac(
        "function resta(a: integer, b: integer): integer { return a - b; }\n"
        "let x: integer = 7;\n"
        "let r: integer = resta(x, 2 * x);\n"
    )
    code = lowered.unit()
    params = [item for item in code if item.opcode is OpCode.PARAM]
    (call,) = calls(code)
    assert len(params) == 2 and call.arg2.value == 2
    assert code.index(params[1]) == code.index(params[0]) + 1 == code.index(call) - 1
    multiply = next(item for item in code if item.opcode is OpCode.MUL)
    assert code.index(multiply) < code.index(params[0])
    assert params[1].arg1 == multiply.result
    assert (call.arg1.kind, call.arg1.value) == (OperandKind.LABEL, "fn_resta")


def test_void_and_valued_calls(generate_tac):
    """A call statement names no result; a call in an expression does."""
    lowered = generate_tac(
        "function avisar(n: integer) { print(n); }\n"
        "function doble(n: integer): integer { return n * 2; }\n"
        "avisar(1);\n"
        "doble(2);\n"
        "let d: integer = doble(3);\n"
    )
    void_call, discarded, valued = calls(lowered.unit())
    assert void_call.result is None and discarded.result is None
    assert valued.result.kind is OperandKind.TEMPORARY and valued.result.type == INTEGER


def test_return_value_and_implicit_void_return(generate_tac):
    """FUN-04: a valued return per path; a void body gets one final return."""
    lowered = generate_tac(
        "function signo(n: integer): integer {\n"
        "  if (n < 0) {\n    return 0 - 1;\n  }\n  return 1;\n}\n"
        "function mostrar(n: integer) {\n  print(n);\n}\n"
    )
    signo = lowered.unit("fn_signo")
    returns = [item for item in signo if item.opcode is OpCode.RETURN]
    assert len(returns) == 2 and all(item.arg1 is not None for item in returns)
    assert signo[-1].opcode is OpCode.RETURN and signo[-1].arg1.value == 1
    mostrar = lowered.unit("fn_mostrar")
    assert mostrar[-1].opcode is OpCode.RETURN and mostrar[-1].arg1 is None
    assert opcodes(mostrar).count(OpCode.RETURN) == 1


def test_no_return_is_appended_after_a_terminal_return(generate_tac):
    code = generate_tac("function f(): integer {\n  return 1;\n}\n").unit("fn_f")
    assert opcodes(code) == [OpCode.RETURN]


def test_integer_arguments_and_returns_are_widened_to_float(generate_tac):
    lowered = generate_tac(
        "function mitad(x: float): float { let n: integer = 1; return n; }\n"
        "let k: integer = 4;\n"
        "let m: float = mitad(k);\n"
    )
    global_code = lowered.unit()
    cast = next(item for item in global_code if item.opcode is OpCode.CAST)
    param = next(item for item in global_code if item.opcode is OpCode.PARAM)
    assert param.arg1 == cast.result and cast.result.type == FLOAT
    body = lowered.unit("fn_mitad")
    returned = body[-1].arg1
    assert body[-1].opcode is OpCode.RETURN and returned.type == FLOAT
    assert any(item.opcode is OpCode.CAST and item.result == returned for item in body)


# -- recursion --------------------------------------------------------------------


def test_recursion_and_forward_calls_from_a_real_program(generate_tac):
    """FUN-05 and FUN-06 with tests/cps/validos/FUN-03-recursion.cps."""
    source = (CPS / "validos" / "FUN-03-recursion.cps").read_text(encoding="utf8")
    lowered = generate_tac(source)
    assert labels_of(lowered) == ["fn_factorial", "fn_esPar", "fn_esImpar"]
    (inner,) = calls(lowered.unit("fn_factorial"))
    assert inner.arg1.value == "fn_factorial"
    assert [c.arg1.value for c in calls(lowered.unit("fn_esPar"))] == ["fn_esImpar"]
    assert [c.arg1.value for c in calls(lowered.unit("fn_esImpar"))] == ["fn_esPar"]
    # the forward call in global code precedes the declaration of esPar
    first_call = calls(lowered.unit())[0]
    assert first_call.arg1.value == "fn_esPar" and first_call.arg2.value == 1
    labels = {item.arg1.value for p in lowered.program.procedures for item in calls(p.instructions)}
    assert labels <= {"fn_factorial", "fn_esPar", "fn_esImpar"}


# -- activation records -----------------------------------------------------------


def test_each_frame_reserves_its_procedures_temporary_peak(generate_tac):
    """TMP-05: frames hold the live peak, not every temporary ever named."""
    lowered = generate_tac(
        "function f(a: integer, b: integer): integer {\n"
        "  let x: integer = (a + 1) * (b + 2);\n"
        "  let y: integer = a + b;\n"
        "  return x + y;\n}\n"
    )
    (procedure,) = lowered.program.procedures
    frame = lowered.layouts.frame_by_label("fn_f")
    assert procedure.temporary_peak == 3
    assert frame.temporary_capacity == procedure.temporary_peak
    frame.require_temporaries(procedure.temporary_peak)
    assert frame.size >= frame.temporaries[-1].end


# -- failures ---------------------------------------------------------------------


def test_break_in_a_function_declared_inside_a_loop_is_rejected(compile_facts):
    """Semantics keeps its loop stack across the declaration; codegen does not."""
    run, facts = compile_facts(
        "while (true) {\n  function salir() {\n    break;\n  }\n  break;\n}\n"
    )
    with pytest.raises(CodegenError, match="IRGEN-BREAK-OUTSIDE-LOOP") as error:
        CompiscriptCodeGenerator(facts).generate(run.syntax_result.tree)
    assert error.value.location.line == 3
