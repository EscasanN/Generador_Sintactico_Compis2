from src.codegen.ir import IRProcedure, IRProgram, Instruction, OpCode, Operand, OperandKind
from src.codegen.verifier import IRVerifier
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import INTEGER


LOC = SourceLocation(1, 1)
ONE = Operand(OperandKind.CONSTANT, 1, INTEGER)
T = Operand(OperandKind.TEMPORARY, "t0", INTEGER, (0, 0))
L = Operand(OperandKind.LABEL, "end")


def codes(*instructions):
    return {item.code for item in IRVerifier().verify(IRProgram(tuple(instructions)))}


def test_verifier_accepts_defined_temporary_and_valid_jump():
    assert codes(
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
        Instruction(OpCode.GOTO, result=L, source_location=LOC),
        Instruction(OpCode.LABEL, result=L, source_location=LOC),
        Instruction(OpCode.PARAM, T, source_location=LOC),
        Instruction(OpCode.CALL, Operand(OperandKind.LABEL, "external"), ONE, source_location=LOC),
        Instruction(OpCode.RELEASE, T, source_location=LOC),
    ) == set()


def test_verifier_reports_undefined_and_released_temporary():
    undefined = codes(Instruction(OpCode.PARAM, T, source_location=LOC))
    assert "IR-TEMP-UNDEFINED" in undefined

    released = codes(
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
        Instruction(OpCode.RELEASE, T, source_location=LOC),
        Instruction(OpCode.PARAM, T, source_location=LOC),
    )
    assert "IR-TEMP-UNDEFINED" in released


def test_verifier_reports_missing_duplicate_labels_and_bad_arity():
    actual = codes(
        Instruction(OpCode.GOTO, result=L, source_location=LOC),
        Instruction(OpCode.LABEL, result=Operand(OperandKind.LABEL, "other"), source_location=LOC),
        Instruction(OpCode.LABEL, result=Operand(OperandKind.LABEL, "other"), source_location=LOC),
        Instruction(OpCode.ADD, ONE, result=T, source_location=LOC),
    )
    assert {"IR-LABEL-MISSING", "IR-LABEL-DUPLICATE", "IR-ARITY"} <= actual


def test_verifier_checks_call_argument_count_and_location():
    actual = codes(
        Instruction(OpCode.PARAM, ONE, source_location=LOC),
        Instruction(
            OpCode.CALL,
            Operand(OperandKind.LABEL, "f"),
            Operand(OperandKind.CONSTANT, 2, INTEGER),
        ),
    )
    assert "IR-CALL-ARITY" in actual
    assert "IR-LOCATION" in actual


def test_verifier_rejects_procedure_without_return():
    procedure = IRProcedure(Operand(OperandKind.LABEL, "f"), (), (
        Instruction(OpCode.PARAM, ONE, source_location=LOC),
    ))
    actual = {item.code for item in IRVerifier().verify(IRProgram((), (procedure,)))}
    assert "IR-PROCEDURE-OPEN" in actual




def test_verifier_accepts_branch_merge_definition():
    condition = Operand(OperandKind.SYMBOL, "flag", INTEGER)
    false_label = Operand(OperandKind.LABEL, "false")
    end = Operand(OperandKind.LABEL, "end")
    assert codes(
        Instruction(OpCode.IF_FALSE, condition, result=false_label, source_location=LOC),
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
        Instruction(OpCode.GOTO, result=end, source_location=LOC),
        Instruction(OpCode.LABEL, result=false_label, source_location=LOC),
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
        Instruction(OpCode.LABEL, result=end, source_location=LOC),
        Instruction(
            OpCode.COPY, T,
            result=Operand(OperandKind.SYMBOL, "x", INTEGER),
            source_location=LOC,
        ),
    ) == set()


def test_verifier_rejects_redefining_a_released_lease():
    actual = codes(
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
        Instruction(OpCode.RELEASE, T, source_location=LOC),
        Instruction(OpCode.COPY, ONE, result=T, source_location=LOC),
    )
    assert "IR-TEMP-STALE" in actual


def test_verifier_rejects_label_operands_in_arithmetic():
    actual = codes(Instruction(OpCode.ADD, L, L, L, LOC))
    assert "IR-OPERAND-KIND" in actual


def test_verifier_checks_operand_kinds_for_reserved_list_and_field_ops():
    actual = codes(Instruction(OpCode.LIST_GET, L, L, L, LOC))
    assert "IR-OPERAND-KIND" in actual


def test_verifier_checks_undefined_temp_even_in_unreachable_code():
    end = Operand(OperandKind.LABEL, "end")
    actual = codes(
        Instruction(OpCode.GOTO, result=end, source_location=LOC),
        Instruction(
            OpCode.COPY, T,
            result=Operand(OperandKind.SYMBOL, "x", INTEGER),
            source_location=LOC,
        ),
        Instruction(OpCode.LABEL, result=end, source_location=LOC),
    )
    assert "IR-TEMP-UNDEFINED" in actual
