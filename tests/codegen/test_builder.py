import pytest

from src.codegen.builder import IRBuilder
from src.codegen.ir import OpCode, Operand, OperandKind
from src.semantic.diagnostics import SourceLocation
from src.semantic.types import INTEGER


LOC = SourceLocation(3, 5)


def test_builder_separates_global_code_and_closed_procedures():
    builder = IRBuilder()
    value = Operand(OperandKind.CONSTANT, 7, INTEGER)
    destination = Operand(OperandKind.SYMBOL, "global@x", INTEGER)
    builder.emit(OpCode.COPY, value, result=destination, location=LOC)
    label = Operand(OperandKind.LABEL, "fn")
    builder.begin_procedure(label, ())
    builder.emit(OpCode.RETURN, value, location=LOC)
    builder.end_procedure()

    program = builder.build()
    assert [item.opcode for item in program.global_code] == [OpCode.COPY]
    assert program.procedures[0].label == label
    assert [item.opcode for item in program.procedures[0].instructions] == [OpCode.RETURN]


def test_builder_rejects_open_procedure_and_stale_temporary_use():
    builder = IRBuilder()
    builder.begin_procedure(Operand(OperandKind.LABEL, "fn"), ())
    with pytest.raises(RuntimeError):
        builder.build()
    builder.end_procedure()

    temporary = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY,
        Operand(OperandKind.CONSTANT, 1, INTEGER),
        result=temporary,
        location=LOC,
    )
    builder.release(temporary, location=LOC)
    with pytest.raises(ValueError):
        builder.emit(
            OpCode.COPY,
            temporary,
            result=Operand(OperandKind.SYMBOL, "x", INTEGER),
            location=LOC,
        )


def test_builder_emits_labels_and_branches_with_locations():
    builder = IRBuilder()
    label = builder.labels.next("done")
    condition = Operand(OperandKind.CONSTANT, False, INTEGER)
    builder.branch_false(condition, label, location=LOC)
    builder.jump(label, location=LOC)
    builder.mark(label, location=LOC)
    assert [item.opcode for item in builder.build().global_code] == [
        OpCode.IF_FALSE, OpCode.GOTO, OpCode.LABEL,
    ]
    assert all(item.source_location == LOC for item in builder.build().global_code)


def test_procedure_temporaries_are_isolated_and_peak_is_retained():
    builder = IRBuilder()
    first = Operand(OperandKind.LABEL, "first")
    builder.begin_procedure(first, ())
    left = builder.temporary(INTEGER)
    right = builder.temporary(INTEGER)
    assert left.value != right.value
    builder.release(left, LOC)
    builder.release(right, LOC)
    builder.emit(OpCode.RETURN, location=LOC)
    completed = builder.end_procedure()
    assert completed.temporary_peak == 2

    builder.begin_procedure(Operand(OperandKind.LABEL, "second"), ())
    again = builder.temporary(INTEGER)
    assert again.value == "t0"
    builder.release(again, LOC)
    builder.emit(OpCode.RETURN, location=LOC)
    builder.end_procedure()


def test_procedure_cannot_close_with_live_temporaries():
    builder = IRBuilder()
    builder.begin_procedure(Operand(OperandKind.LABEL, "fn"), ())
    builder.temporary(INTEGER)
    builder.emit(OpCode.RETURN, location=LOC)
    with pytest.raises(RuntimeError):
        builder.end_procedure()


def test_return_consumes_temporary_and_closes_procedure():
    from src.codegen.verifier import IRVerifier

    builder = IRBuilder()
    builder.begin_procedure(Operand(OperandKind.LABEL, "fn"), ())
    result = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY,
        Operand(OperandKind.CONSTANT, 7, INTEGER),
        result=result,
        location=LOC,
    )
    builder.emit(OpCode.RETURN, result, location=LOC)
    builder.end_procedure()
    assert [item.opcode for item in builder.build().procedures[0].instructions] == [
        OpCode.COPY, OpCode.RETURN,
    ]
    assert IRVerifier().verify(builder.build()) == ()


def test_return_in_one_branch_does_not_recycle_live_name_in_other_branch():
    from src.codegen.verifier import IRVerifier

    builder = IRBuilder()
    builder.begin_procedure(Operand(OperandKind.LABEL, "fn"), ())
    original = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY,
        Operand(OperandKind.CONSTANT, 1, INTEGER),
        result=original,
        location=LOC,
    )
    other_branch = builder.labels.next("else")
    builder.branch_false(Operand(OperandKind.CONSTANT, False, INTEGER), other_branch, LOC)
    builder.emit(OpCode.RETURN, original, location=LOC)
    builder.mark(other_branch, LOC)
    replacement = builder.temporary(INTEGER)
    assert replacement.value != original.value
    builder.emit(
        OpCode.COPY,
        Operand(OperandKind.CONSTANT, 2, INTEGER),
        result=replacement,
        location=LOC,
    )
    builder.emit(OpCode.RETURN, replacement, location=LOC)
    builder.end_procedure()
    assert IRVerifier().verify(builder.build()) == ()


def test_same_live_value_can_return_from_two_exclusive_branches():
    from src.codegen.verifier import IRVerifier

    builder = IRBuilder()
    builder.begin_procedure(Operand(OperandKind.LABEL, "fn"), ())
    result = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY,
        Operand(OperandKind.CONSTANT, 1, INTEGER),
        result=result,
        location=LOC,
    )
    other = builder.labels.next("other")
    builder.branch_false(Operand(OperandKind.CONSTANT, False, INTEGER), other, LOC)
    builder.emit(OpCode.RETURN, result, location=LOC)
    builder.mark(other, LOC)
    builder.emit(OpCode.RETURN, result, location=LOC)
    builder.end_procedure()
    assert IRVerifier().verify(builder.build()) == ()
