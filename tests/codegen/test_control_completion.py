"""Reachable returns and exception-handler lifetime across transfers."""

import pytest

from src.codegen.ir import IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.pipeline import compile_compiscript
from src.codegen.verifier import IRVerifier
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import INTEGER


@pytest.mark.parametrize("body", [
    "", "if (b) { return 1; }", "while (false) { return 1; }",
    "while (true) { if (b) { break; } }",
])
def test_reachable_missing_return_rejects_without_partial_tac(body):
    result = compile_compiscript(f"function f(b:boolean):integer {{ {body} }} let r=f(false);")
    assert result.semantic_result.accepted
    assert result.failed_stage == "codegen" and not result.tac
    assert {d.code for d in result.intermediate_result.diagnostics} == {"IRGEN-MISSING-RETURN"}
    assert result.intermediate_result.diagnostics[0].location.line == 1


@pytest.mark.parametrize("body", [
    "if (b) { return 1; } else { return 2; }",
    "while (true) { continue; }", "for (;;) { continue; }",
    "do { print(1); } while (true);",
])
def test_complete_returns_or_proven_nontermination_are_accepted(body):
    result = compile_compiscript(f"function f(b:boolean):integer {{ {body} }}")
    assert result.accepted, result.intermediate_result and result.intermediate_result.diagnostics


@pytest.mark.parametrize("transfer", ["break;", "continue;", "return 1;"])
def test_leaving_try_removes_the_handler_before_the_transfer(transfer):
    source = (
        f"function f():integer {{ while (true) {{ try {{ {transfer} }} "
        "catch (err) { return 2; } } return 3; }"
    )
    result = compile_compiscript(source)
    assert result.accepted, result.intermediate_result and result.intermediate_result.diagnostics
    code = result.intermediate_result.program.procedures[0].instructions
    begin = next(i for i, item in enumerate(code) if item.opcode is OpCode.TRY_BEGIN)
    transfer_index = next(i for i in range(begin + 1, len(code))
                          if code[i].opcode in (OpCode.GOTO, OpCode.RETURN))
    assert code[transfer_index - 1].opcode is OpCode.TRY_END


def test_a_loop_inside_try_does_not_remove_the_outer_handler():
    result = compile_compiscript("try { while (true) { break; } print(1); } catch (err) { print(err); }")
    assert result.accepted
    code = result.intermediate_result.program.global_code
    leave = next(i for i, item in enumerate(code)
                 if item.opcode is OpCode.GOTO and str(item.result.value).startswith("while_end"))
    assert code[leave - 1].opcode is not OpCode.TRY_END


def test_exception_edge_keeps_temporaries_defined_before_try_alive_in_catch():
    loc = SourceLocation(1, 1)
    one = Operand(OperandKind.CONSTANT, 1, INTEGER)
    temp = Operand(OperandKind.TEMPORARY, "t0", INTEGER, (0, 0))
    catch = Operand(OperandKind.LABEL, "catch")
    out = Operand(OperandKind.SYMBOL, "x", INTEGER)
    program = IRProgram((
        Instruction(OpCode.COPY, one, result=temp, source_location=loc),
        Instruction(OpCode.TRY_BEGIN, result=catch, source_location=loc),
        Instruction(OpCode.RETURN, source_location=loc),
        Instruction(OpCode.LABEL, result=catch, source_location=loc),
        Instruction(OpCode.CATCH, result=out, source_location=loc),
        Instruction(OpCode.COPY, temp, result=out, source_location=loc),
        Instruction(OpCode.RELEASE, temp, source_location=loc),
    ))
    assert IRVerifier().verify(program) == ()
